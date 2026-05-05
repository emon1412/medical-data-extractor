"""Persistence for the Order aggregate."""
# Defer all annotation evaluation: our `list(...)` method shadows the
# built-in, so eager evaluation (Python 3.12 default in production) breaks
# any later `list[...]` type annotation in this class with a confusing
# "'function' object is not subscriptable" error. Local Python 3.14
# defers annotations by default and hides the bug.
from __future__ import annotations

from typing import Optional, Protocol, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.schemas.order import OrderCreate, OrderUpdate


class OrderRepositoryProtocol(Protocol):
    """Public contract for any Order persistence backend.

    Depend on this in controllers / services so the concrete backend can be
    swapped (e.g. with a fake in unit tests) without touching call-sites.
    """

    def create(self, payload: OrderCreate) -> Order: ...

    def get(self, order_id: str) -> Optional[Order]: ...

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: Optional[OrderStatus] = None,
        search: Optional[str] = None,
    ) -> Tuple[list[Order], int]: ...

    def update(self, order: Order, payload: OrderUpdate) -> Order: ...

    def delete(self, order: Order) -> None: ...


class OrderRepository:
    """SQLAlchemy implementation of :class:`OrderRepositoryProtocol`."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: OrderCreate, *, patient_id: str | None = None) -> Order:
        data = payload.model_dump()
        if patient_id is not None:
            data["patient_id"] = patient_id
        order = Order(**data)
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get(self, order_id: str) -> Optional[Order]:
        return self.db.get(Order, order_id)

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: Optional[OrderStatus] = None,
        search: Optional[str] = None,
    ) -> Tuple[list[Order], int]:
        stmt = select(Order)
        count_stmt = select(func.count()).select_from(Order)

        if status is not None:
            stmt = stmt.where(Order.status == status)
            count_stmt = count_stmt.where(Order.status == status)

        if search:
            like = f"%{search.lower()}%"
            name_filter = (
                func.lower(Order.patient_first_name).like(like)
                | func.lower(Order.patient_last_name).like(like)
            )
            stmt = stmt.where(name_filter)
            count_stmt = count_stmt.where(name_filter)

        stmt = stmt.order_by(Order.created_at.desc()).limit(limit).offset(offset)

        items = self.db.execute(stmt).scalars().all()
        total = self.db.execute(count_stmt).scalar_one()
        return list(items), int(total)

    def list_for_patient(
        self, patient_id: str, *, limit: int = 50, offset: int = 0
    ) -> Tuple[list[Order], int]:
        stmt = (
            select(Order)
            .where(Order.patient_id == patient_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        count_stmt = (
            select(func.count()).select_from(Order).where(Order.patient_id == patient_id)
        )
        items = self.db.execute(stmt).scalars().all()
        total = self.db.execute(count_stmt).scalar_one()
        return list(items), int(total)

    def update(self, order: Order, payload: OrderUpdate) -> Order:
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(order, k, v)
        self.db.commit()
        self.db.refresh(order)
        return order

    def delete(self, order: Order) -> None:
        self.db.delete(order)
        self.db.commit()
