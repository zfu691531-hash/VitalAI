"""Minimal admin authentication for side-effecting control endpoints."""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status

ADMIN_TOKEN_ENV = "VITALAI_ADMIN_TOKEN"
ADMIN_TOKEN_HEADER = "X-VitalAI-Admin-Token"


def _configured_admin_token() -> str | None:
    """Return the configured admin token, if one is present."""
    token = os.getenv(ADMIN_TOKEN_ENV, "").strip()
    return token or None


def require_admin_token(
    admin_token: str | None = Header(default=None, alias=ADMIN_TOKEN_HEADER),
) -> None:
    """Require the configured admin token for control-plane routes."""
    configured_token = _configured_admin_token()
    if configured_token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Admin control token is not configured. Set {ADMIN_TOKEN_ENV} before using admin endpoints.",
        )

    if admin_token is None or not hmac.compare_digest(admin_token, configured_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token.",
        )
