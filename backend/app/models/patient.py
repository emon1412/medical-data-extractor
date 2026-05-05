"""Patient ORM model — first-class entity that orders reference."""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint(
            "first_name_lower",
            "last_name_lower",
            "dob",
            name="uq_patients_identity",
        ),
        Index("ix_patients_last_first", "last_name_lower", "first_name_lower"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)

    first_name_lower: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    last_name_lower: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    orders = relationship("Order", back_populates="patient", lazy="selectin")
