"""Pub/Sub webhook verification boundary for Gmail notifications."""
from flask import Request


def verify_oidc_request(request: Request, audience: str) -> bool:
    """Require a bearer token; production deployments should validate it with Google auth."""
    header = request.headers.get("Authorization", "")
    return bool(audience and header.startswith("Bearer "))
