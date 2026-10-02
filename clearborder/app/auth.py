"""Optional API-key authentication (X-API-Key header)."""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str | None:
    """Accept every request when no key is configured; otherwise require a known key."""
    if not settings.allowed_api_keys:
        return None
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key header")
    if api_key not in settings.allowed_api_keys:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
    return api_key
