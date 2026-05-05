"""Controller for PDF upload + patient information extraction."""
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.order import OrderStatus
from app.schemas.extraction import ExtractionResponse
from app.schemas.order import OrderCreate
from app.repositories.order_repository import OrderRepository
from app.repositories.patient_repository import PatientRepository
from app.services.extraction import extract_patient_info
from app.services.extraction_cache import extraction_cache, hash_bytes
from app.services.pdf_text import extract_text_from_pdf


class ExtractionController:
    @staticmethod
    async def extract_from_pdf(
        db: Session,
        file: UploadFile,
        create_order: bool = False,
    ) -> ExtractionResponse:
        settings = get_settings()

        # Validate content-type
        content_type = (file.content_type or "").lower()
        if content_type not in settings.allowed_upload_mime_type_list:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"Unsupported file type '{content_type}'. "
                    f"Allowed: {', '.join(settings.allowed_upload_mime_type_list)}"
                ),
            )

        # Read with size limit
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        contents = await file.read(max_bytes + 1)
        if len(contents) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {settings.max_upload_size_mb} MB",
            )
        if not contents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty"
            )

        # Quick PDF magic-bytes check
        if not contents.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File does not appear to be a valid PDF",
            )

        # Content-hash dedupe: if we've already extracted the same byte-for-byte
        # PDF on this container, return the cached patient info. Saves an LLM
        # round-trip and demonstrably costs less. The text-preview is omitted
        # for cache hits since we no longer have the parsed text.
        content_hash = hash_bytes(contents)
        cached = extraction_cache.get(content_hash)

        text = ""
        if cached is None:
            try:
                text = extract_text_from_pdf(contents)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Could not read PDF contents: {e}",
                )

            # When text extraction returns nothing (scanned PDF), pass the PDF
            # bytes through to the LLM. OpenAI's Responses API accepts PDFs
            # directly and handles OCR + page-image extraction server-side, so
            # we don't need to render anything ourselves.
            extracted = extract_patient_info(
                text,
                pdf_bytes=contents,
                pdf_filename=file.filename or "document.pdf",
            )
            extraction_cache.put(content_hash, extracted)
        else:
            extracted = cached
            # Mark the source so callers can tell this came from the cache,
            # which is genuinely useful for debugging "wait, why did this come
            # back in 50 ms?".
            extracted.source = f"{extracted.source}+cache"

        order_id: Optional[str] = None
        if create_order:
            if not extracted.first_name or not extracted.last_name:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Cannot create order: patient first or last name could not be extracted. "
                        "Re-upload with create_order=false to inspect the result, or create the "
                        "order manually."
                    ),
                )

            patient = PatientRepository(db).find_or_create(
                first_name=extracted.first_name,
                last_name=extracted.last_name,
                dob=extracted.date_of_birth,
            )
            order_payload = OrderCreate(
                patient_first_name=extracted.first_name,
                patient_last_name=extracted.last_name,
                patient_dob=extracted.date_of_birth,
                status=OrderStatus.PENDING,
                source_document_name=file.filename,
                extraction_confidence=extracted.confidence,
                # Persist the rich extracted fields (prescriber, diagnoses,
                # ordered items, address, etc.) alongside the order so the
                # full document context is queryable later.
                document_metadata=(
                    extracted.document.model_dump(mode="json")
                    if extracted.document is not None
                    else None
                ),
            )
            order = OrderRepository(db).create(order_payload, patient_id=patient.id)
            order_id = order.id

        return ExtractionResponse(
            extracted=extracted,
            raw_text_preview=(text or "")[:500],
            order_id=order_id,
        )
