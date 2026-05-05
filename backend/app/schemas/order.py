"""Pydantic schemas for the Order resource."""
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.order import OrderStatus


class OrderBase(BaseModel):
    patient_first_name: str = Field(min_length=1, max_length=120)
    patient_last_name: str = Field(min_length=1, max_length=120)
    patient_dob: Optional[date] = None
    status: OrderStatus = OrderStatus.PENDING
    notes: Optional[str] = Field(default=None, max_length=4000)
    source_document_name: Optional[str] = Field(default=None, max_length=255)
    extraction_confidence: Optional[str] = Field(default=None, max_length=20)
    document_metadata: Optional[dict[str, Any]] = None

    @field_validator("patient_first_name", "patient_last_name")
    @classmethod
    def strip_names(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("patient_dob")
    @classmethod
    def validate_dob_not_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("date of birth cannot be in the future")
        return v


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    patient_first_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    patient_last_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    patient_dob: Optional[date] = None
    status: Optional[OrderStatus] = None
    notes: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("patient_dob")
    @classmethod
    def validate_dob_not_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("date of birth cannot be in the future")
        return v


class OrderRead(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    items: list[OrderRead]
    total: int
    limit: int
    offset: int
