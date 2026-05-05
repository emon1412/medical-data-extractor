"""Integration tests for the PDF extraction endpoint.

Generates a tiny PDF on the fly so we don't depend on external assets, and
verifies the endpoint correctly parses patient info via the regex path
(no LLM required).
"""
import io

try:
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, TextStringObject
except ImportError:  # pragma: no cover
    PdfWriter = None  # type: ignore


def _make_pdf_with_text(text: str) -> bytes:
    """Build a minimal PDF containing the given text using a hand-rolled stream."""
    # Use a basic PDF with one text content stream
    lines = text.split("\n")
    y = 750
    content_ops = ["BT", "/F1 12 Tf"]
    for line in lines:
        # Escape parens and backslashes
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_ops.append(f"1 0 0 1 50 {y} Tm")
        content_ops.append(f"({safe}) Tj")
        y -= 16
    content_ops.append("ET")
    stream = "\n".join(content_ops).encode("latin-1")

    objects = []

    def add(obj_bytes: bytes) -> int:
        objects.append(obj_bytes)
        return len(objects)

    pages_id = 2
    page_id = 3
    font_id = 4
    contents_id = 5

    # 1 - Catalog
    add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode())
    # 2 - Pages
    add(f"<< /Type /Pages /Kids [{page_id} 0 R] /Count 1 >>".encode())
    # 3 - Page
    add(
        (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
            f"/Contents {contents_id} 0 R >>"
        ).encode()
    )
    # 4 - Font
    add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    # 5 - Contents
    contents_obj = (
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
    )
    add(contents_obj)

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode())
        out.write(obj)
        out.write(b"\nendobj\n")
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n".encode())
    out.write(f"startxref\n{xref_pos}\n%%EOF\n".encode())
    return out.getvalue()


def test_extract_pdf_with_patient(client):
    pdf_bytes = _make_pdf_with_text(
        "Medical Order\n"
        "First Name: Sarah\n"
        "Last Name: Connor\n"
        "Date of Birth: 05/15/1985\n"
    )

    r = client.post(
        "/api/v1/extractions/pdf",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
        data={"create_order": "false"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["extracted"]["first_name"] == "Sarah"
    assert data["extracted"]["last_name"] == "Connor"
    assert data["extracted"]["date_of_birth"] == "1985-05-15"


def test_extract_pdf_create_order(client):
    pdf_bytes = _make_pdf_with_text(
        "Patient Name: John Smith\nDOB: 1970-12-01"
    )
    r = client.post(
        "/api/v1/extractions/pdf",
        files={"file": ("intake.pdf", pdf_bytes, "application/pdf")},
        data={"create_order": "true"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["order_id"]

    # Verify the order persisted
    r2 = client.get(f"/api/v1/orders/{data['order_id']}")
    assert r2.status_code == 200
    o = r2.json()
    assert o["patient_first_name"] == "John"
    assert o["patient_last_name"] == "Smith"
    assert o["source_document_name"] == "intake.pdf"


def test_reject_non_pdf(client):
    r = client.post(
        "/api/v1/extractions/pdf",
        files={"file": ("not.txt", b"hello", "text/plain")},
        data={"create_order": "false"},
    )
    assert r.status_code == 415


def test_reject_invalid_pdf_bytes(client):
    r = client.post(
        "/api/v1/extractions/pdf",
        files={"file": ("fake.pdf", b"not a real pdf", "application/pdf")},
        data={"create_order": "false"},
    )
    assert r.status_code == 400


def test_reject_empty_file(client):
    r = client.post(
        "/api/v1/extractions/pdf",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        data={"create_order": "false"},
    )
    assert r.status_code == 400
