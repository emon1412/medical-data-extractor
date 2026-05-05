"""Order ORM model."""
import enum
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # Denormalised patient identity columns — kept for fast list/search and so
    # an order is meaningful even if the patient row is later anonymised.
    patient_first_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    patient_last_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    patient_dob: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Canonical link to the Patient aggregate. Nullable because manual order
    # creation may skip linking, and to keep backward compatibility with rows
    # created before the patient table existed.
    patient_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    patient = relationship("Patient", back_populates="orders", lazy="joined")

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extraction_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Free-form structured data extracted from the source document — prescriber,
    # diagnoses, items ordered, address, etc. Stored as JSON so the schema can
    # evolve without migrations.
    document_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
