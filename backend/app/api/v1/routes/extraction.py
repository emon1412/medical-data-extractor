"""HTTP routes for document upload + patient extraction."""
from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.controllers.extraction_controller import ExtractionController
from app.core.config import get_settings
from app.core.security import require_api_key
from app.db.session import get_db
from app.middleware.rate_limit import limiter
from app.schemas.extraction import ExtractionResponse

router = APIRouter(
    prefix="/extractions",
    tags=["extractions"],
    dependencies=[Depends(require_api_key)],
)


_settings = get_settings()


@router.post(
    "/pdf",
    response_model=ExtractionResponse,
    summary="Upload a PDF and extract patient information",
)
@limiter.limit(_settings.rate_limit_upload)
async def extract_pdf(
    request: Request,  # required by slowapi
    response: Response,
    file: UploadFile = File(..., description="PDF document"),
    create_order: bool = Form(False, description="If true, persist an Order from the extraction"),
    db: Session = Depends(get_db),
) -> ExtractionResponse:
    result = await ExtractionController.extract_from_pdf(db, file, create_order=create_order)
    if result.order_id:
        response.headers["X-Resource-ID"] = result.order_id
    return result
