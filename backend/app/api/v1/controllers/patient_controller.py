"""Controller for the Patient resource (read-only via the API; created
implicitly by the extraction flow)."""
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.data_services.order_data_service import OrderDataService
from app.data_services.patient_data_service import PatientDataService
from app.schemas.order import OrderListResponse, OrderRead
from app.schemas.patient import PatientListResponse, PatientRead


def _to_read(repo: PatientDataService, p) -> PatientRead:
    data = PatientRead.model_validate(p)
    data.order_count = repo.order_count(p.id)
    return data


class PatientController:
    @staticmethod
    def list(
        db: Session, *, limit: int, offset: int, search: Optional[str]
    ) -> PatientListResponse:
        repo = PatientDataService(db)
        items, total = repo.list(limit=limit, offset=offset, search=search)
        return PatientListResponse(
            items=[_to_read(repo, p) for p in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def get(db: Session, patient_id: str) -> PatientRead:
        repo = PatientDataService(db)
        p = repo.get(patient_id)
        if p is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found",
            )
        return _to_read(repo, p)

    @staticmethod
    def list_orders(
        db: Session, patient_id: str, *, limit: int, offset: int
    ) -> OrderListResponse:
        if PatientDataService(db).get(patient_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found",
            )
        order_repo = OrderDataService(db)
        items, total = order_repo.list_for_patient(
            patient_id, limit=limit, offset=offset
        )
        return OrderListResponse(
            items=[OrderRead.model_validate(o) for o in items],
            total=total,
            limit=limit,
            offset=offset,
        )
