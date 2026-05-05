"""Pydantic schemas for activity logs."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ActivityLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    method: str
    path: str
    status_code: int
    duration_ms: int
    action: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    actor: Optional[str]
    client_ip: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    error_message: Optional[str]
    created_at: datetime


class ActivityLogListResponse(BaseModel):
    items: list[ActivityLogRead]
    total: int
    limit: int
    offset: int
