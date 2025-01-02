import functools
import json
import time
from datetime import datetime, timezone
from typing import Callable

from odoo.http import request
from .managers import TokenManager
from .response import APIResponse
from .utils import make_serializable


def require_authenticated_client(func: Callable) -> Callable:
    """
    Decorator to enforce authentication for API endpoints using Bearer tokens.

    This decorator ensures that the incoming API request contains a valid
    Bearer token in the `Authorization` header. It performs several checks:

    1. **Authorization Header Validation:**
       - Verifies the presence of the `Authorization` header.
       - Ensures the header starts with the "Bearer " prefix.

    2. **Token Decoding and Validation:**
       - Decodes the access token to retrieve the payload.
       - Checks the existence of the token record in the database.

    3. **Client and Token Status Checks:**
       - Confirms that the client associated with the token is active.
       - Verifies that the token has not expired.
       - Validates the token's signature using the client's secret.

    4. **Client Attachment:**
       - Attaches the authenticated client to the `kwargs` for downstream use in the controller.

    **Note:** This decorator should be applied to controller methods that require
    authenticated access. It should be placed **after** any logging decorators
    (like `@log_request_decorator`)


    Args:
        func (Callable): The controller method to be decorated. This method will
                         only be executed if authentication is successful.

    Returns:
        Callable: The wrapped controller method with enforced authentication.

    Raises:
        APIResponse: Returns an API error response if authentication fails due to
                     missing/invalid headers, inactive clients, expired tokens,
                     or invalid signatures.
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


def log_request(func: Callable) -> Callable:
    """
    Decorator to log API request details, including duration, status code, and other metadata.

    Note: Use this decorator **before** `@require_authenticated_client`, to catch all requests, if
    you are not interested in logging unauthenticated requests then place it after
    `@require_authenticated_client`


    Args:
        func (Callable): The controller method to be decorated.

    Returns:
        Callable: The wrapped controller method with logging functionality.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        status_code = 200
        client_id = None

        try:
            # Attempt to extract client ID from Authorization header
            # This is useful for logging requests without requiring authentication
            # (e.g., for public endpoints)
            auth_header = request.httprequest.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split("Bearer ")[1]
                try:
                    token_record = TokenManager.get_token_record(token, request.env)
                    if token_record:
                        client_id = token_record.client_id.id
                except Exception:
                    pass  # Silently handle token lookup failures

            response = func(*args, **kwargs)
            if isinstance(response, dict) and "status_code" in response:
                status_code = response.get("status_code", 200)
            elif hasattr(response, "status_code"):
                status_code = response.status_code
            return response
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            raise
        finally:
            end_time = time.time()
            duration = end_time - start_time
            env = request.env
            values = {
                "endpoint": request.httprequest.path,
                "method": request.httprequest.method,
                "request_params": json.dumps(make_serializable(kwargs or {})),
                "status_code": status_code,
                "client_id": client_id or kwargs.get("client", {}).get("id"),
                "ip_address": request.httprequest.remote_addr,
                "user_agent": request.httprequest.user_agent.string,
                "duration": duration,
            }

            env["akm.request.log"].sudo().create(values)

    return wrapper
