"""Rate limiter shared across the app (slowapi)."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def _key(request) -> str:
    """Use the API key as the rate-limit key when present, else fall back to IP."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_key, default_limits=[get_settings().rate_limit_default])
