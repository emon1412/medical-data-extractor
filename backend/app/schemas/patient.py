"""Pydantic schemas for the Patient resource."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PatientBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    dob: Optional[date] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("dob")
    @classmethod
    def _no_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("date of birth cannot be in the future")
        return v


class PatientCreate(PatientBase):
    pass


class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_count: int = 0
    created_at: datetime
    updated_at: datetime


class PatientListResponse(BaseModel):
    items: list[PatientRead]
    total: int
    limit: int
    offset: int
