"""Repository layer — encapsulates all database access for the application.

Controllers and services depend on the *Protocol* interfaces here, not on the
concrete SQLAlchemy implementations. That makes the persistence layer trivially
swappable (e.g. for an in-memory fake during tests, or a different backend later)
and keeps SQL out of the business-logic layer.
"""
from app.repositories.activity_log_repository import (
    ActivityLogRepository,
    ActivityLogRepositoryProtocol,
)
from app.repositories.order_repository import (
    OrderRepository,
    OrderRepositoryProtocol,
)
from app.repositories.patient_repository import (
    PatientRepository,
    PatientRepositoryProtocol,
)

__all__ = [
    "OrderRepository",
    "OrderRepositoryProtocol",
    "ActivityLogRepository",
    "ActivityLogRepositoryProtocol",
    "PatientRepository",
    "PatientRepositoryProtocol",
]
