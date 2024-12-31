import functools
from odoo.http import request
from .managers import TokenManager
from ..config.response import APIResponse
from datetime import datetime, timezone


def require_authenticated_client(func):
    """
    Decorator to require a valid access token for API endpoints.

    It expects the access token to be provided in the Authorization header as a Bearer token.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.httprequest.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return APIResponse.error(
                message="Missing or invalid Authorization header",
                error_code="UNAUTHORIZED",
                status_code=401,
            )

        access_token = auth_header.split("Bearer ")[1]

        # Decode the token to get payload
        payload = TokenManager.decode_payload(access_token)
        if not payload:
            return APIResponse.error(
                message="Invalid token payload",
                error_code="INVALID_TOKEN",
                status_code=401,
            )

        # Retrieve token record
        token_record = TokenManager.get_token_record(access_token, request.env)
        if not token_record:
            return APIResponse.error(
                message="Token not found",
                error_code="INVALID_TOKEN",
                status_code=401,
            )

        # Check if token's client is active
        client_id = token_record.client_id.id
        if not TokenManager.is_client_active(client_id, request.env):
            return APIResponse.error(
                message="Client associated with the token is inactive",
                error_code="INACTIVE_CLIENT",
                status_code=401,
            )

        # Check token expiration
        if datetime.now(timezone.utc).timestamp() > payload.get("exp", 0):
            return APIResponse.error(
                message="Token has expired",
                error_code="TOKEN_EXPIRED",
                status_code=401,
            )

        # Validate token signature
        if not TokenManager.validate_signature(
            access_token, token_record.client_id.client_secret
        ):
            return APIResponse.error(
                message="Invalid token signature",
                error_code="INVALID_SIGNATURE",
                status_code=401,
            )

        # Attach the client to kwargs
        kwargs["client"] = token_record.client_id

        return func(*args, **kwargs)

    return wrapper
