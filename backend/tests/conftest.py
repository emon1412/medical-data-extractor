"""Shared test fixtures: real Postgres + isolated TestClient.

Tests require a reachable Postgres instance. Locally:

    docker compose up -d postgres
    pytest

CI provides one via the `services.postgres` block in .github/workflows/ci.yml.
The DATABASE_URL env var (set below if absent) points at the dockerised
default. The schema is created once per session and tables are TRUNCATEd
between tests for isolation.
"""
import os

# Configure env BEFORE importing the app
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://hde:hde@localhost:5434/medical_data",
)
os.environ.setdefault("REQUIRE_AUTH", "false")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RATE_LIMIT_DEFAULT", "1000/minute")
os.environ.setdefault("RATE_LIMIT_UPLOAD", "1000/minute")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Reset cached settings since we mutated env above
get_settings.cache_clear()


@pytest.fixture(scope="session")
def db_engine():
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url, future=True, pool_pre_ping=True)
    try:
        # Make sure we can actually connect; otherwise skip the whole suite
        # with a useful message instead of a wall of red.
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as e:
        pytest.skip(f"Postgres not reachable at {url!r}: {e}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _truncate_tables(db_engine):
    """Wipe data between tests for full isolation (fast on a small schema)."""
    yield
    table_names = ", ".join(
        f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
    )
    with db_engine.begin() as conn:
        conn.exec_driver_sql(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")


@pytest.fixture()
def client(db_engine, monkeypatch):
    TestingSession = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False, future=True
    )

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Middleware uses SessionLocal directly — point it at the test session too.
    import app.middleware.activity_logger as al_mw
    import app.db.session as db_session
    monkeypatch.setattr(al_mw, "SessionLocal", TestingSession)
    monkeypatch.setattr(db_session, "SessionLocal", TestingSession)

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
