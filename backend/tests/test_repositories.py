"""Direct unit tests for the repository layer.

These exercise the persistence code without going through the HTTP stack,
and double as a check that our concrete repos honour their Protocols.
"""
from sqlalchemy.orm import sessionmaker

from app.models.order import OrderStatus
from app.repositories.activity_log_repository import (
    ActivityLogRepository,
    ActivityLogRepositoryProtocol,
)
from app.repositories.order_repository import (
    OrderRepository,
    OrderRepositoryProtocol,
)
from app.schemas.order import OrderCreate, OrderUpdate


def _session(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_order_repo_implements_protocol():
    # Static check: assignment compiles iff the concrete class structurally
    # satisfies the Protocol. Catches drift between repo and contract.
    repo: OrderRepositoryProtocol = OrderRepository(db=None)  # type: ignore[arg-type]
    assert hasattr(repo, "create")


def test_activity_log_repo_implements_protocol():
    repo: ActivityLogRepositoryProtocol = ActivityLogRepository(db=None)  # type: ignore[arg-type]
    assert hasattr(repo, "create")


def test_order_repo_full_lifecycle(db_engine):
    db = _session(db_engine)
    repo = OrderRepository(db)

    created = repo.create(
        OrderCreate(
            patient_first_name="Ada",
            patient_last_name="Lovelace",
            patient_dob=None,
        )
    )
    assert created.id

    fetched = repo.get(created.id)
    assert fetched is not None
    assert fetched.patient_first_name == "Ada"

    updated = repo.update(fetched, OrderUpdate(status=OrderStatus.COMPLETED))
    assert updated.status == OrderStatus.COMPLETED

    items, total = repo.list(limit=10, offset=0)
    assert total == 1
    assert items[0].id == created.id

    items, total = repo.list(limit=10, offset=0, search="lovelace")
    assert total == 1

    items, total = repo.list(limit=10, offset=0, status=OrderStatus.PENDING)
    assert total == 0

    repo.delete(updated)
    assert repo.get(created.id) is None


def test_activity_log_repo_create_and_list(db_engine):
    db = _session(db_engine)
    repo = ActivityLogRepository(db)

    repo.create(
        method="GET",
        path="/api/v1/orders",
        status_code=200,
        duration_ms=12,
        actor="test",
    )
    repo.create(
        method="POST",
        path="/api/v1/orders",
        status_code=201,
        duration_ms=34,
        actor="test",
    )

    items, total = repo.list(limit=10, offset=0)
    assert total == 2

    items, total = repo.list(limit=10, offset=0, path_contains="orders")
    assert total == 2
    assert all("orders" in i.path for i in items)
