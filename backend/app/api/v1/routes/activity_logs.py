"""HTTP routes for read-only access to the activity log."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.controllers.activity_log_controller import ActivityLogController
from app.core.security import require_api_key
from app.db.session import get_db
from app.schemas.activity_log import ActivityLogListResponse

router = APIRouter(
    prefix="/activity-logs",
    tags=["activity-logs"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=ActivityLogListResponse, summary="List activity log entries")
def list_activity_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    path_contains: Optional[str] = Query(None, description="Filter by URL path substring"),
    action: Optional[str] = Query(
        None, description="Filter by semantic action name (e.g. 'order.created')"
    ),
    resource_type: Optional[str] = Query(
        None, description="Filter by resource type (e.g. 'order', 'extraction')"
    ),
    resource_id: Optional[str] = Query(
        None, description="Filter by resource id — useful for 'what happened to order X?' queries"
    ),
    db: Session = Depends(get_db),
) -> ActivityLogListResponse:
    return ActivityLogController.list(
        db,
        limit=limit,
        offset=offset,
        path_contains=path_contains,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
    )
