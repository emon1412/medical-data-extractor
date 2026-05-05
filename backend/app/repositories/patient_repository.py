"""Persistence for the Patient aggregate."""
# Same reason as order_repository.py: defer annotation evaluation so the
# `list(...)` method doesn't shadow the built-in and break later
# `list[...]` annotations on Python 3.12.
from __future__ import annotations

from datetime import date
from typing import Optional, Protocol, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.patient import Patient


class PatientRepositoryProtocol(Protocol):
    def get(self, patient_id: str) -> Optional[Patient]: ...

    def find_by_identity(
        self, *, first_name: str, last_name: str, dob: Optional[date]
    ) -> Optional[Patient]: ...

    def find_or_create(
        self, *, first_name: str, last_name: str, dob: Optional[date]
    ) -> Patient: ...

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> Tuple[list[Patient], int]: ...


class PatientRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, patient_id: str) -> Optional[Patient]:
        return self.db.get(Patient, patient_id)

    def find_by_identity(
        self, *, first_name: str, last_name: str, dob: Optional[date]
    ) -> Optional[Patient]:
        stmt = select(Patient).where(
            Patient.first_name_lower == first_name.strip().lower(),
            Patient.last_name_lower == last_name.strip().lower(),
            Patient.dob == dob,
        )
        return self.db.execute(stmt).scalars().first()

    def find_or_create(
        self, *, first_name: str, last_name: str, dob: Optional[date]
    ) -> Patient:
        first_name = first_name.strip()
        last_name = last_name.strip()
        existing = self.find_by_identity(first_name=first_name, last_name=last_name, dob=dob)
        if existing is not None:
            return existing

        patient = Patient(
            first_name=first_name,
            last_name=last_name,
            dob=dob,
            first_name_lower=first_name.lower(),
            last_name_lower=last_name.lower(),
        )
        self.db.add(patient)
        try:
            self.db.commit()
            self.db.refresh(patient)
            return patient
        except Exception:
            # Race: someone inserted the same identity between our find and
            # our insert. Roll back and re-fetch.
            self.db.rollback()
            existing = self.find_by_identity(
                first_name=first_name, last_name=last_name, dob=dob
            )
            if existing is None:
                raise
            return existing

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> Tuple[list[Patient], int]:
        stmt = select(Patient)
        count_stmt = select(func.count()).select_from(Patient)

        if search:
            like = f"%{search.lower()}%"
            name_filter = (
                Patient.first_name_lower.like(like) | Patient.last_name_lower.like(like)
            )
            stmt = stmt.where(name_filter)
            count_stmt = count_stmt.where(name_filter)

        stmt = stmt.order_by(Patient.last_name_lower.asc(), Patient.first_name_lower.asc())
        stmt = stmt.limit(limit).offset(offset)

        items = self.db.execute(stmt).scalars().all()
        total = self.db.execute(count_stmt).scalar_one()
        return list(items), int(total)

    def order_count(self, patient_id: str) -> int:
        # Lazy import to avoid model circular import on startup
        from app.models.order import Order

        return int(
            self.db.execute(
                select(func.count()).select_from(Order).where(Order.patient_id == patient_id)
            ).scalar_one()
        )
