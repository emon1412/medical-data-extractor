"""Persist a record of every API request to the database.

Captures both HTTP-level audit info (method, path, status, duration, IP, UA)
AND a semantic view (action verb, resource_type, resource_id) so the audit
log is usable for "what happened to order X?" style queries, not just URL
string searches.
"""
import logging
import re
import time
from typing import Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.db.session import SessionLocal, ensure_schema
from app.repositories.activity_log_repository import ActivityLogRepository

logger = logging.getLogger(__name__)


# Paths we don't want to clutter the activity log with
_SKIP_PATHS = {
    "/",
    "/favicon.ico",
    "/health",
    "/api/v1/health",
    "/api/v1/health/db",
    "/api/v1/health/llm",
    "/docs",
    "/redoc",
    "/openapi.json",
}


# Map (method, path-pattern) -> (action_verb, resource_type, capture-group-name-for-id-or-None)
_ROUTE_RULES: list[tuple[str, re.Pattern[str], str, str, Optional[int]]] = [
    # Orders
    ("POST",   re.compile(r"^/api/v1/orders/?$"),                    "order.created",     "order",      None),
    ("GET",    re.compile(r"^/api/v1/orders/?$"),                    "order.listed",      "order",      None),
    ("GET",    re.compile(r"^/api/v1/orders/(?P<id>[^/]+)/?$"),      "order.read",        "order",      1),
    ("PATCH",  re.compile(r"^/api/v1/orders/(?P<id>[^/]+)/?$"),      "order.updated",     "order",      1),
    ("DELETE", re.compile(r"^/api/v1/orders/(?P<id>[^/]+)/?$"),      "order.deleted",     "order",      1),
    # Patients
    ("GET",    re.compile(r"^/api/v1/patients/?$"),                  "patient.listed",    "patient",    None),
    ("GET",    re.compile(r"^/api/v1/patients/(?P<id>[^/]+)/?$"),    "patient.read",      "patient",    1),
    ("GET",    re.compile(r"^/api/v1/patients/(?P<id>[^/]+)/orders/?$"),
                                                                     "patient.orders.read", "patient", 1),
    # Extractions
    ("POST",   re.compile(r"^/api/v1/extractions/pdf/?$"),           "extraction.run",    "extraction", None),
    # Activity log (read)
    ("GET",    re.compile(r"^/api/v1/activity-logs/?$"),             "activity.listed",   "activity",   None),
]


def _classify(method: str, path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (action, resource_type, resource_id) for a request.

    Falls back to (None, None, None) for unknown routes — those still get the
    raw HTTP fields persisted, just no semantic tagging.
    """
    for rule_method, pattern, action, resource_type, id_group in _ROUTE_RULES:
        if rule_method != method:
            continue
        m = pattern.match(path)
        if not m:
            continue
        resource_id = m.group("id") if id_group is not None else None
        return action, resource_type, resource_id
    return None, None, None


class ActivityLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        error_message: str | None = None
        status_code = 500
        response: Response | None = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            error_message = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            path = request.url.path

            # NOTE: never `return` from a `finally` block in middleware — the
            # try-block is already returning the response, and a return here
            # would shadow it with None. Use a guard instead.
            if path not in _SKIP_PATHS and not path.startswith(("/static", "/_next")):
                try:
                    actor = request.headers.get("X-API-Key")
                    actor_label = "api-key" if actor else "anonymous"
                    client_ip = request.client.host if request.client else None
                    forwarded_for = request.headers.get("x-forwarded-for")
                    if forwarded_for:
                        client_ip = forwarded_for.split(",")[0].strip()

                    request_id = getattr(request.state, "request_id", None)

                    action, resource_type, resource_id = _classify(request.method, path)
                    if response is not None and resource_id is None:
                        response_resource_id = response.headers.get("X-Resource-ID")
                        if response_resource_id:
                            resource_id = response_resource_id

                    ensure_schema()
                    db = SessionLocal()
                    try:
                        ActivityLogRepository(db).create(
                            method=request.method,
                            path=path,
                            status_code=status_code,
                            duration_ms=duration_ms,
                            action=action,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            actor=actor_label,
                            client_ip=client_ip,
                            user_agent=request.headers.get("user-agent"),
                            request_id=request_id,
                            error_message=error_message,
                        )
                    finally:
                        db.close()
                except Exception as log_err:  # pragma: no cover
                    logger.warning("Failed to persist activity log: %s", log_err)
