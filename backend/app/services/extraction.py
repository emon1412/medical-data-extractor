"""Patient information extraction.

Strategy:
1. Try LLM (OpenAI) for high-accuracy structured extraction with JSON schema.
2. Fall back to regex/heuristics on the raw text if LLM isn't configured or fails.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from datetime import date, datetime
from typing import List, Optional

from app.core.config import get_settings
from app.schemas.extraction import (
    Address,
    Diagnosis,
    DocumentDetails,
    OrderedItem,
    PatientExtraction,
    Prescriber,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%m/%d/%y",
    "%d/%m/%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
]


def _parse_date(s: str) -> Optional[date]:
    s = s.strip().rstrip(".,;:")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# LLM extraction
# ---------------------------------------------------------------------------

_LLM_SYSTEM = (
    "You are a precise medical document parser. Extract structured data from "
    "the provided medical/order document. If a value is not clearly present, "
    "return null (or omit list items) — do not invent, paraphrase, or guess. "
    "Respond with strict JSON only, matching the schema in the user message."
)


_RICH_JSON_SCHEMA_HINT = """\
Respond with JSON matching this schema EXACTLY (omit array items rather than
inventing them; use null for unknown scalars):

{
  "first_name": string|null,
  "last_name": string|null,
  "date_of_birth": "YYYY-MM-DD"|null,
  "confidence": "high"|"medium"|"low",
  "document": {
    "document_type": string|null,
    "order_date": "YYYY-MM-DD"|null,
    "patient_address": {
      "line1": string|null, "line2": string|null,
      "city": string|null, "state": string|null, "postal_code": string|null
    }|null,
    "prescriber": {
      "name": string|null, "npi": string|null,
      "phone": string|null, "fax": string|null,
      "address": { "line1": string|null, "line2": string|null,
                   "city": string|null, "state": string|null,
                   "postal_code": string|null }|null
    }|null,
    "diagnoses": [ { "code": string|null, "description": string|null }, ... ],
    "items":     [ { "code": string|null, "description": string|null,
                     "side": "LT"|"RT"|"Bilateral"|null,
                     "quantity": integer|null }, ... ]
  }|null
}
"""


def _coerce_address(d: Optional[dict]) -> Optional[Address]:
    if not isinstance(d, dict):
        return None
    a = Address(
        line1=(d.get("line1") or None),
        line2=(d.get("line2") or None),
        city=(d.get("city") or None),
        state=(d.get("state") or None),
        postal_code=(d.get("postal_code") or None),
    )
    return a if any(a.model_dump().values()) else None


def _coerce_prescriber(d: Optional[dict]) -> Optional[Prescriber]:
    if not isinstance(d, dict):
        return None
    p = Prescriber(
        name=(d.get("name") or None),
        npi=(d.get("npi") or None),
        phone=(d.get("phone") or None),
        fax=(d.get("fax") or None),
        address=_coerce_address(d.get("address")),
    )
    return p if any(
        v is not None for v in [p.name, p.npi, p.phone, p.fax, p.address]
    ) else None


def _coerce_document(d: Optional[dict]) -> Optional[DocumentDetails]:
    if not isinstance(d, dict):
        return None

    order_date_raw = d.get("order_date")
    order_date: Optional[date] = None
    if order_date_raw:
        try:
            order_date = datetime.strptime(order_date_raw, "%Y-%m-%d").date()
        except ValueError:
            order_date = _parse_date(order_date_raw)

    diagnoses: list[Diagnosis] = []
    for raw in d.get("diagnoses") or []:
        if isinstance(raw, dict) and (raw.get("code") or raw.get("description")):
            diagnoses.append(
                Diagnosis(
                    code=(raw.get("code") or None),
                    description=(raw.get("description") or None),
                )
            )

    items: list[OrderedItem] = []
    for raw in d.get("items") or []:
        if not isinstance(raw, dict):
            continue
        if not any([raw.get("code"), raw.get("description")]):
            continue
        try:
            qty = int(raw["quantity"]) if raw.get("quantity") is not None else None
        except (TypeError, ValueError):
            qty = None
        items.append(
            OrderedItem(
                code=(raw.get("code") or None),
                description=(raw.get("description") or None),
                side=(raw.get("side") or None),
                quantity=qty,
            )
        )

    doc = DocumentDetails(
        document_type=(d.get("document_type") or None),
        order_date=order_date,
        patient_address=_coerce_address(d.get("patient_address")),
        prescriber=_coerce_prescriber(d.get("prescriber")),
        diagnoses=diagnoses,
        items=items,
    )
    populated = (
        doc.document_type
        or doc.order_date
        or doc.patient_address
        or doc.prescriber
        or doc.diagnoses
        or doc.items
    )
    return doc if populated else None


# Models that support the new `reasoning_effort` parameter (GPT-5.x family + o-series).
# Older models (gpt-4o, gpt-4o-mini, gpt-4-turbo) reject this kwarg.
_REASONING_MODEL_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def _supports_reasoning(model: str) -> bool:
    return any(model.startswith(p) for p in _REASONING_MODEL_PREFIXES)


def _build_llm_kwargs(settings, *, max_output_tokens: int) -> dict:
    """Build provider kwargs that work for both reasoning and chat-only models."""
    kwargs: dict = {
        "model": settings.openai_model,
        "response_format": {"type": "json_object"},
    }
    if _supports_reasoning(settings.openai_model):
        # Reasoning models (gpt-5.x, o-series) use `max_completion_tokens` and
        # accept `reasoning_effort` for latency / cost control.
        kwargs["max_completion_tokens"] = max_output_tokens
        kwargs["reasoning_effort"] = settings.openai_reasoning_effort
    else:
        # Older chat-only models (gpt-4o, gpt-4o-mini, etc.) use the legacy params.
        kwargs["max_tokens"] = max_output_tokens
        kwargs["temperature"] = 0
    return kwargs


def _parse_llm_response(content: str, *, source: str) -> PatientExtraction:
    """Coerce an LLM JSON response into a typed PatientExtraction.

    Handles both the legacy slim schema (first/last/dob only) and the rich
    schema (with `document` block) — falling back to None for any field
    that's missing or malformed.
    """
    try:
        data = json.loads(content) if content else {}
    except json.JSONDecodeError:
        data = {}

    dob_raw = data.get("date_of_birth")
    dob: Optional[date] = None
    if dob_raw:
        try:
            dob = datetime.strptime(dob_raw, "%Y-%m-%d").date()
        except ValueError:
            dob = _parse_date(dob_raw)

    first = (data.get("first_name") or "").strip() or None
    last = (data.get("last_name") or "").strip() or None
    confidence = (data.get("confidence") or "low").lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"

    return PatientExtraction(
        first_name=first,
        last_name=last,
        date_of_birth=dob,
        confidence=confidence,
        source=source,
        document=_coerce_document(data.get("document")),
    )


def _extract_with_llm_pdf(pdf_bytes: bytes, *, filename: str = "document.pdf") -> Optional[PatientExtraction]:
    """Send the raw PDF directly to OpenAI via the Responses API.

    GPT-5.4 (and other vision-capable models) extract both text AND page
    images from the PDF server-side, so we don't need to render anything
    ourselves. This is what lets the production function stay slim — we
    don't ship `pypdfium2` or `Pillow`.

    Used as the high-quality path for both scanned PDFs (where text
    extraction returns nothing) and digital PDFs where we want the model
    to see the layout, not just a flat text dump.
    """
    settings = get_settings()
    if not settings.openai_api_key or not pdf_bytes:
        return None

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)

        b64 = base64.b64encode(pdf_bytes).decode("ascii")

        kwargs: dict = {
            "model": settings.openai_model,
            "input": [
                {"role": "system", "content": _LLM_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": _RICH_JSON_SCHEMA_HINT},
                        {
                            "type": "input_file",
                            "filename": filename,
                            "file_data": f"data:application/pdf;base64,{b64}",
                        },
                    ],
                },
            ],
            "text": {"format": {"type": "json_object"}},
            "max_output_tokens": 2000,
        }
        if _supports_reasoning(settings.openai_model):
            kwargs["reasoning"] = {"effort": settings.openai_reasoning_effort}

        response = client.responses.create(**kwargs)

        # `response.output_text` is the SDK's convenience accessor that
        # concatenates all text outputs into a single string. It's the
        # right choice when we asked for `text.format = json_object`.
        content = (getattr(response, "output_text", None) or "").strip() or "{}"
        return _parse_llm_response(content, source="llm_pdf")
    except Exception as e:
        logger.warning("LLM PDF extraction failed: %s", e)
        return None


def _extract_with_llm(text: str) -> Optional[PatientExtraction]:
    settings = get_settings()
    if not settings.openai_api_key:
        return None

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds)

        # Truncate very long documents to keep cost & latency in check.
        # GPT-5.4 supports 1M tokens of context but we only need a few KB to find a name.
        truncated = text[:12000]

        user_msg = (
            "Extract the patient information from the following medical/order document.\n"
            f"{_RICH_JSON_SCHEMA_HINT}\n"
            f"Document text:\n---\n{truncated}\n---"
        )

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": _LLM_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            **_build_llm_kwargs(settings, max_output_tokens=2000),
        )
        return _parse_llm_response(
            response.choices[0].message.content or "{}", source="llm"
        )
    except Exception as e:
        logger.warning("LLM extraction failed, falling back to regex: %s", e)
        return None


# ---------------------------------------------------------------------------
# Regex / heuristic extraction (fallback)
# ---------------------------------------------------------------------------

# Words that signal the end of a name field (i.e. the next labeled section starts)
_NAME_STOP_WORDS = {
    "dob",
    "date",
    "birth",
    "born",
    "mrn",
    "ssn",
    "id",
    "phone",
    "address",
    "patient",
    "gender",
    "sex",
    "age",
    "insurance",
    "physician",
    "provider",
    "doctor",
    "ordering",
    "procedure",
    "diagnosis",
    "icd",
    "cpt",
    "account",
}

_NAME_LABEL_PATTERNS = [
    re.compile(r"patient\s*name\s*[:\-]\s*([^\n\r]+)", re.IGNORECASE),
    re.compile(r"(?<!\w)name\s*[:\-]\s*([^\n\r]+)", re.IGNORECASE),
    re.compile(r"(?<!\w)patient\s*[:\-]\s*([^\n\r]+)", re.IGNORECASE),
]

_FIRST_NAME_PATTERN = re.compile(r"first\s*name\s*[:\-]\s*([A-Za-z][A-Za-z'\-]*)", re.IGNORECASE)
_LAST_NAME_PATTERN = re.compile(r"last\s*name\s*[:\-]\s*([A-Za-z][A-Za-z'\-]*)", re.IGNORECASE)

_DOB_LABEL_PATTERN = re.compile(
    r"(?:date\s*of\s*birth|d\.?\s*o\.?\s*b\.?|birth\s*date|born)\s*[:\-]?\s*"
    r"([A-Za-z0-9,\.\-/ ]{6,40})",
    re.IGNORECASE,
)

_LASTNAME_FIRSTNAME_PATTERN = re.compile(
    r"(?:patient\s*)?name\s*[:\-]\s*([A-Za-z'\-]+)\s*,\s*([A-Za-z'\-]+)", re.IGNORECASE
)


def _clean_name_tokens(s: str) -> list[str]:
    """Split a captured name string into clean tokens, stopping at label words.

    Drops middle initials (single letters or letter+period).
    """
    tokens: list[str] = []
    for raw in re.split(r"\s+", s.strip()):
        token = raw.strip(",.;:")
        if not token:
            continue
        # Stop if we hit the start of another labeled field
        if token.lower().rstrip(":") in _NAME_STOP_WORDS:
            break
        # Drop if it looks like a label-with-colon like "DOB:"
        if ":" in token:
            head = token.split(":", 1)[0]
            if head.lower() in _NAME_STOP_WORDS:
                break
        # Skip middle initials (single letter, optionally with period)
        if re.fullmatch(r"[A-Za-z]\.?", token):
            continue
        # Names should look like names — letters, hyphens, apostrophes only
        if not re.fullmatch(r"[A-Za-z][A-Za-z'\-]*", token):
            break
        tokens.append(token)
    return tokens


def _extract_with_regex(text: str) -> PatientExtraction:
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dob: Optional[date] = None

    # 1) Explicit "First Name: X" and "Last Name: Y" labels
    fn_match = _FIRST_NAME_PATTERN.search(text)
    ln_match = _LAST_NAME_PATTERN.search(text)
    if fn_match:
        first_name = fn_match.group(1).strip()
    if ln_match:
        last_name = ln_match.group(1).strip()

    # 2) "Name: Last, First"
    if not (first_name and last_name):
        m = _LASTNAME_FIRSTNAME_PATTERN.search(text)
        if m:
            last_name, first_name = m.group(1).strip(), m.group(2).strip()

    # 3) "Patient Name: First [Middle] Last"
    if not (first_name and last_name):
        for pat in _NAME_LABEL_PATTERNS:
            m = pat.search(text)
            if not m:
                continue
            tokens = _clean_name_tokens(m.group(1))
            if len(tokens) >= 2:
                first_name = first_name or tokens[0]
                last_name = last_name or tokens[-1]
                break
            elif len(tokens) == 1 and not first_name:
                first_name = tokens[0]

    # DOB
    for m in _DOB_LABEL_PATTERN.finditer(text):
        candidate = m.group(1).strip().split("\n")[0]
        for i in range(len(candidate), 5, -1):
            parsed = _parse_date(candidate[:i])
            if parsed:
                dob = parsed
                break
        if dob:
            break

    if first_name and last_name and dob:
        confidence: str = "medium"
    elif first_name and last_name:
        confidence = "low"
    else:
        confidence = "low"

    return PatientExtraction(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=dob,
        confidence=confidence,
        source="regex",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def extract_patient_info(
    text: str,
    *,
    pdf_bytes: Optional[bytes] = None,
    pdf_filename: str = "document.pdf",
) -> PatientExtraction:
    """Extract patient info from a document.

    Strategy:
      1. If we have meaningful text, try the chat-completions LLM (cheap path),
         then regex fallback.
      2. If no usable text *and* we have the original PDF bytes + an OpenAI key,
         send the PDF directly via the Responses API (model handles all OCR &
         page-image extraction server-side; no need for us to render).
      3. Always return a PatientExtraction (fields may be None).
    """
    has_text = bool(text and text.strip())

    if has_text:
        llm_result = _extract_with_llm(text)
        if llm_result and (
            llm_result.first_name or llm_result.last_name or llm_result.date_of_birth
        ):
            if not llm_result.date_of_birth:
                regex_result = _extract_with_regex(text)
                if regex_result.date_of_birth:
                    llm_result.date_of_birth = regex_result.date_of_birth
            return llm_result

        regex_result = _extract_with_regex(text)
        if regex_result.first_name or regex_result.last_name or regex_result.date_of_birth:
            return regex_result

    # No usable text — send the PDF directly to OpenAI for vision-grade OCR.
    if pdf_bytes:
        pdf_result = _extract_with_llm_pdf(pdf_bytes, filename=pdf_filename)
        if pdf_result:
            return pdf_result

    return PatientExtraction(confidence="low", source="regex")
