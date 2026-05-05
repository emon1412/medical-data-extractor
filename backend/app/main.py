"""FastAPI application factory + entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.middleware.activity_logger import ActivityLoggerMiddleware
from app.middleware.error_handlers import register_exception_handlers
from app.middleware.rate_limit import limiter
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    try:
        init_db()
        logger.info(
            "Database initialised (%s)", get_settings().database_url.split("://")[0]
        )
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to initialise database: %s", e)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging("DEBUG" if settings.debug else "INFO")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=_lifespan,
        description=(
            "REST API for managing patient orders and extracting structured data "
            "from uploaded medical PDF documents."
        ),
    )

    # ---- Middleware (order matters: outermost first) ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-ms"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(ActivityLoggerMiddleware)

    # Rate limiting
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Global error handlers
    register_exception_handlers(app)

    # Routers
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api": "/api/v1",
        }

    return app


app = create_app()
