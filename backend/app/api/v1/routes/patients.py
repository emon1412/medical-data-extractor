"""HTTP routes for the Patient resource (read-only)."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.controllers.patient_controller import PatientController
from app.core.security import require_api_key
from app.db.session import get_db
from app.schemas.order import OrderListResponse
from app.schemas.patient import PatientListResponse, PatientRead

router = APIRouter(
    prefix="/patients",
    tags=["patients"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=PatientListResponse, summary="List patients")
def list_patients(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(
        None, description="Search by first or last name (case-insensitive)"
    ),
    db: Session = Depends(get_db),
) -> PatientListResponse:
    return PatientController.list(db, limit=limit, offset=offset, search=search)


@router.get(
    "/{patient_id}",
    response_model=PatientRead,
    summary="Get a single patient",
)
def get_patient(patient_id: str, db: Session = Depends(get_db)) -> PatientRead:
    return PatientController.get(db, patient_id)


@router.get(
    "/{patient_id}/orders",
    response_model=OrderListResponse,
    summary="List all orders for a patient",
)
def list_patient_orders(
    patient_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> OrderListResponse:
    return PatientController.list_orders(
        db, patient_id, limit=limit, offset=offset
    )
