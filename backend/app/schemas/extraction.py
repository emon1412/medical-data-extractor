"""Schemas for the document extraction endpoint."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class Address(BaseModel):
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None


class Prescriber(BaseModel):
    name: Optional[str] = None
    npi: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    address: Optional[Address] = None


class Diagnosis(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None


class OrderedItem(BaseModel):
    code: Optional[str] = Field(None, description="HCPCS / CPT / product code")
    description: Optional[str] = None
    side: Optional[str] = Field(None, description="LT / RT / Bilateral / etc.")
    quantity: Optional[int] = None


class DocumentDetails(BaseModel):
    """Everything we extract from the source document beyond the patient
    identity. All fields are optional — the LLM is asked to omit anything
    not clearly present rather than guessing."""

    document_type: Optional[str] = None
    order_date: Optional[date] = None
    patient_address: Optional[Address] = None
    prescriber: Optional[Prescriber] = None
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    items: list[OrderedItem] = Field(default_factory=list)


class PatientExtraction(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    confidence: str = Field(default="low", description="One of: high, medium, low")
    source: str = Field(default="regex", description="Extraction source: 'llm' / 'llm_vision' / 'regex'")
    document: Optional[DocumentDetails] = None


class ExtractionResponse(BaseModel):
    extracted: PatientExtraction
    raw_text_preview: str = Field(default="", description="First 500 chars of extracted document text")
    order_id: Optional[str] = Field(
        default=None, description="If create_order=true, the id of the persisted order"
    )
