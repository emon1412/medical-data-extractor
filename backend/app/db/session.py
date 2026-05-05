"""Database engine, session factory, and FastAPI dependency."""
import logging
import threading
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def _normalise_database_url(url: str) -> str:
    """Coerce common Postgres URL variants to use the psycopg3 driver.

    Hosted-Postgres providers (Cloud SQL, Neon, Supabase, RDS) typically
    inject ``postgresql://...`` or the legacy ``postgres://...``. SQLAlchemy
    needs an explicit driver suffix to use psycopg3 (which is what we ship in
    requirements.txt). Doing this here means the operator can paste the URL
    they're given verbatim and it just works.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


_database_url = _normalise_database_url(settings.database_url)


def _connect_args_for(url: str) -> dict:
    if url.startswith("postgresql+psycopg"):
        # Disable prepared statements for psycopg3. This is required when running
        # against a pooled Postgres connection in transaction mode (e.g. pgBouncer
        # in transaction mode, RDS Proxy) and is harmless on direct connections.
        # Without this, the second use of any prepared statement on a recycled
        # backend session raises: "prepared statement does not exist".
        return {"prepare_threshold": None}
    return {}


engine = create_engine(
    _database_url,
    connect_args=_connect_args_for(_database_url),
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# --- Lazy schema initialisation ---------------------------------------------
# Cloud Run fires FastAPI lifespan events normally, so `init_db` runs from the
# `_lifespan` hook in app.main. We also keep a lazy first-request initialiser
# (`ensure_schema`) as a safety net for environments where lifespan is skipped
# (e.g. some test harnesses). It is idempotent and tolerant of failure (we log
# and let the actual query produce the real error).

_schema_lock = threading.Lock()
_schema_ready = False


def init_db() -> None:
    """Create all tables and additively add any missing columns.

    Strategy:
      1. `create_all` creates tables that don't exist yet (idempotent).
      2. `_add_missing_columns` runs ALTER TABLE ADD COLUMN for any column
         our models declare that the DB doesn't have. This is the
         "MVP migration" — covers the 99% case (we only ever add columns,
         never rename or drop). For destructive schema changes, use real
         migrations (Alembic).
    """
    from app import models  # noqa: F401  — register models on Base.metadata

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """Detect and add columns the model declares but the DB is missing."""
    from sqlalchemy import inspect
    from sqlalchemy.schema import CreateColumn

    insp = inspect(engine)
    dialect = engine.dialect

    with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if not insp.has_table(table_name):
                continue
            existing = {c["name"] for c in insp.get_columns(table_name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                # Build a portable column DDL spec
                col_spec = CreateColumn(column).compile(dialect=dialect)
                logger.info(
                    "Adding missing column %s.%s", table_name, column.name
                )
                conn.exec_driver_sql(
                    f'ALTER TABLE "{table_name}" ADD COLUMN {col_spec}'
                )


def ensure_schema() -> None:
    """Run `init_db` exactly once per process (thread-safe, fail-tolerant)."""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        try:
            init_db()
            logger.info("Database schema ready (%s)", _database_url.split("://")[0])
            _schema_ready = True
        except Exception:
            # Don't block the request — let the real query surface the error
            # (e.g. wrong URL, network problem) with a meaningful message.
            logger.exception("ensure_schema failed; continuing without marking ready")


def get_db() -> Generator[Session, None, None]:
    ensure_schema()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
