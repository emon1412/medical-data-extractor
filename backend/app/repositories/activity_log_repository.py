"""Persistence for the ActivityLog audit trail."""
# Same reason as order_repository.py: defer annotation evaluation so the
# `list(...)` method doesn't shadow the built-in and break later
# `list[...]` annotations on Python 3.12.
from __future__ import annotations

from typing import Optional, Protocol, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog


class ActivityLogRepositoryProtocol(Protocol):
    def create(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: int,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> ActivityLog: ...

    def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        path_contains: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> Tuple[list[ActivityLog], int]: ...


class ActivityLogRepository:
    """SQLAlchemy implementation of :class:`ActivityLogRepositoryProtocol`."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: int,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> ActivityLog:
        entry = ActivityLog(
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor=actor,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            error_message=error_message,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        path_contains: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> Tuple[list[ActivityLog], int]:
        stmt = select(ActivityLog)
        count_stmt = select(func.count()).select_from(ActivityLog)

        if path_contains:
            like = f"%{path_contains}%"
            stmt = stmt.where(ActivityLog.path.like(like))
            count_stmt = count_stmt.where(ActivityLog.path.like(like))
        if action:
            stmt = stmt.where(ActivityLog.action == action)
            count_stmt = count_stmt.where(ActivityLog.action == action)
        if resource_type:
            stmt = stmt.where(ActivityLog.resource_type == resource_type)
            count_stmt = count_stmt.where(ActivityLog.resource_type == resource_type)
        if resource_id:
            stmt = stmt.where(ActivityLog.resource_id == resource_id)
            count_stmt = count_stmt.where(ActivityLog.resource_id == resource_id)

        stmt = stmt.order_by(ActivityLog.created_at.desc()).limit(limit).offset(offset)

        items = self.db.execute(stmt).scalars().all()
        total = self.db.execute(count_stmt).scalar_one()
        return list(items), int(total)
