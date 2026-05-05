"""Aggregate v1 router."""
from fastapi import APIRouter

from app.api.v1.routes import (
    activity_logs,
    extraction,
    health,
    orders,
    patients,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(orders.router)
api_router.include_router(patients.router)
api_router.include_router(extraction.router)
api_router.include_router(activity_logs.router)
