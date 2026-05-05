"""Controller for the activity log resource (read-only)."""
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.activity_log_repository import ActivityLogRepository
from app.schemas.activity_log import ActivityLogListResponse, ActivityLogRead


class ActivityLogController:
    @staticmethod
    def list(
        db: Session,
        *,
        limit: int,
        offset: int,
        path_contains: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> ActivityLogListResponse:
        items, total = ActivityLogRepository(db).list(
            limit=limit,
            offset=offset,
            path_contains=path_contains,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        return ActivityLogListResponse(
            items=[ActivityLogRead.model_validate(i) for i in items],
            total=total,
            limit=limit,
            offset=offset,
        )
