"""
Authentication API Router for WebUI Gateway

This router provides backward-compatible authentication endpoints
for the legacy frontend authentication flow.
"""

from typing import Any, Dict

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class NonceRequest(BaseModel):
    """Request model for nonce authentication"""

    nonce: str


class TokenResponse(BaseModel):
    """Response model for token authentication"""

    access_token: str


@router.post("/nonce")
async def auth_nonce(request: NonceRequest) -> Dict[str, Any]:
    """
    Authentication nonce endpoint for backward compatibility.

    In the original system, this created a token message from a nonce.
    For now, we'll return a simple success response to allow authentication.
    """
    # For backward compatibility, return empty success response
    # The original system returned an empty dict when token was None
    return {}


@router.post("/token")
async def auth_token(request: Request) -> TokenResponse:
    """
    Authentication token endpoint for backward compatibility.

    In the original system, this decoded and decrypted a token.
    For now, we'll return a dummy access token to allow authentication.
    """
    # For backward compatibility, return a dummy access token
    # This allows the frontend authentication to succeed
    return TokenResponse(access_token="dummy_access_token_for_development")


@router.get("/health")
async def auth_health_check() -> Dict[str, Any]:
    """Health check for the authentication service"""
    return {
        "status": "healthy",
        "service": "auth-service",
        "message": "Authentication endpoints available",
    }
