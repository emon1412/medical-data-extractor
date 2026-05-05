"""Authentication helpers (simple API-key auth for the MVP)."""
from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> str:
    """Validate the X-API-Key header against the configured key.

    Auth can be disabled by setting REQUIRE_AUTH=false (useful for local dev / tests).
    """
    if not settings.require_auth:
        return "anonymous"

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return x_api_key
