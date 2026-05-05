"""Extract text from a PDF byte stream.

Image rendering for vision-LLM extraction used to live here too, but is now
handled by OpenAI server-side via the Responses API's `input_file` content
type — which means we no longer ship `pypdfium2` or `Pillow` in production.
"""
import io
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text using pdfplumber when available, else pypdf.

    pdfplumber is only used for local dev / tests (it isn't shipped to
    production) — pypdf is the production fallback and is bundled in
    `api/requirements.txt`.
    """
    text = ""
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page in pdf.pages:
                try:
                    pages.append(page.extract_text() or "")
                except Exception as e:  # pragma: no cover
                    logger.warning("pdfplumber page extract failed: %s", e)
            text = "\n".join(pages).strip()
    except Exception as e:
        logger.debug("pdfplumber unavailable, falling back to pypdf: %s", e)

    if text:
        return text

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception as e:  # pragma: no cover
                logger.warning("pypdf page extract failed: %s", e)
        text = "\n".join(pages).strip()
    except Exception as e:
        logger.error("pypdf extraction failed: %s", e)
        raise

    return text
