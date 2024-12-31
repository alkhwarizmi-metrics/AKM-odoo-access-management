# addons/{MODULE_NAME}/controllers/akm_oauth2_controllers.py
from odoo import http, fields
from odoo.http import request
from ..config.response import APIResponse
from ..config.constants import ACCESS_TOKEN_EXPIRY, API_PREFIX
from ..config.utils import validate_http4_url
import json
import secrets


class AkmOAuth2Controller(http.Controller):

    @http.route(
        f"{API_PREFIX}/register",
        type="json",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def register_client(self, **kwargs):
        """
        Register a new OAuth client.

        This endpoint allows an external application to register a new OAuth client
        by providing the application name and redirect URI. The client_id and
        client_secret are automatically generated and returned in the response.

        Expects:
            JSON payload with:
            - name (str): The name of the application.
            - redirect_uri (str): The redirect URI for the application.

        Returns:
            JSON response with:
            - name (str): The name of the application.
            - client_id (str): The generated client ID.
            - client_secret (str): The generated client secret.
            - redirect_uri (str): The redirect URI for the application.
        """
        try:
            # Parse JSON data from the request body
            data = json.loads(request.httprequest.data.decode("utf-8"))
        except json.JSONDecodeError:
            return APIResponse.error(
                message="Invalid JSON payload",
                error_code="INVALID_JSON",
                status_code=400,
            )

        name = data.get("name")
        redirect_uri = data.get("redirect_uri")

        # Basic validation
        if not name or not redirect_uri:

            return APIResponse.error(
                message="Missing required fields",
                error_code="INVALID_REQUEST",
                details={
                    "required": ["name", "redirect_uri"],
                    "provided": {
                        "name": bool(name),
                        "redirect_uri": bool(redirect_uri),
                    },
                },
            )

        if not validate_http4_url(redirect_uri):
            return APIResponse.error(
                message="Invalid redirect_uri",
                error_code="INVALID_REQUEST",
            )

        # Create client record
        client_obj = request.env["akm.oauth.client"].sudo()
        new_client = client_obj.create(
            {
                "name": name,
                "redirect_uri": redirect_uri,
                # client_id/client_secret are automatically generated
            }
        )

        # Re-read from DB to get final stored fields
        new_client_data = new_client.read(
            ["name", "client_id", "client_secret", "redirect_uri"]
        )[0]
        return APIResponse.success(
            data={
                "name": new_client_data["name"],
                "client_id": new_client_data["client_id"],
                "client_secret": new_client_data["client_secret"],
                "redirect_uri": new_client_data["redirect_uri"],
            }
        )

    @http.route(f"{API_PREFIX}/authorize", type="http", auth="user", website=True)
    def authorize(self, **kwargs):
        """
        Step 1: User-facing consent screen
        - Must be logged in (auth='user')
        - Checks client_id validity
        - Renders a QWeb template to allow/deny
        """
        client_id = kwargs.get("client_id")
        response_type = kwargs.get("response_type", "code")
        scope = kwargs.get("scope", "read")

        # To avoid CSRF attacks, we generate a random state parameter
        state = kwargs.get("state", secrets.token_urlsafe(16))

        if response_type != "code":
            return "Unsupported response_type, only 'code' is supported"

        if not client_id:
            return "Missing client_id"

        # Fetch client
        client = (
            request.env["akm.oauth.client"]
            .sudo()
            .search([("client_id", "=", client_id)], limit=1)
        )

        if not client:
            return "Invalid client_id"

        redirect_uri = client.redirect_uri

        # Store 'state' in session for later verification
        request.session["oauth_state"] = state

        # Render consent screen template
        return request.render(
            "alkhwarizmi_metrics_api.akm_oauth_consent_form",
            {
                "client": client,
                "scope": scope,
                "redirect_uri": redirect_uri,
                "state": state,
                "api_prefix": API_PREFIX,
            },
        )

    @http.route(
        f"{API_PREFIX}/confirm", type="http", auth="user", methods=["POST"], csrf=False
    )
    def confirm(self, **kwargs):
        """
        Step 2: Confirming or denying user consent
        - If user approves, generate an auth code
        - If user denies, redirect with error
        """
        decision = kwargs.get("decision")
        client_id = kwargs.get("client_id")
        scope = kwargs.get("scope", "read")
        state = kwargs.get("state")

        stored_state = request.session.get("oauth_state")
        if not state or not stored_state or state != stored_state:
            return "Invalid state parameter"

        # Clear 'state' from session
        request.session.pop("oauth_state", None)

        # Validate client
        client = (
            request.env["akm.oauth.client"]
            .sudo()
            .search([("client_id", "=", client_id)], limit=1)
        )

        if not client:
            return "Invalid client_id"

        redirect_uri = client.redirect_uri

        if decision == "allow":
            # Create authorization code
            AuthCode = request.env["akm.oauth.authcode"].sudo()
            code_record = AuthCode.create_code(client, user_name=client.name)

            # Build redirect URL
            separator = "&" if "?" in redirect_uri else "?"
            final_uri = f"{redirect_uri}{separator}code={code_record.code}&scope={scope}&state={state}"

            # Use direct external redirect
            return request.make_response(
                "",
                headers={"Location": final_uri, "Cache-Control": "no-cache"},
                status=302,
            )
        else:
            # Handle denial
            separator = "&" if "?" in redirect_uri else "?"
            final_uri = f"{redirect_uri}{separator}error=access_denied&state={state}"

            return request.make_response(
                "",
                headers={"Location": final_uri, "Cache-Control": "no-cache"},
                status=302,
            )

    @http.route(
        f"{API_PREFIX}/token", type="json", auth="none", methods=["POST"], csrf=False
    )
    def token(self, **kwargs):
        """
        Step 3: Exchange auth code for access token
        - grant_type=authorization_code
        - Requires valid client_id/client_secret
        - Returns JSON with access_token, refresh_token, etc.
        """
        try:
            # Parse JSON data from the request body
            data = json.loads(request.httprequest.data.decode("utf-8"))
        except json.JSONDecodeError:
            return APIResponse.error(
                message="Invalid JSON payload",
                error_code="INVALID_JSON",
                status_code=400,
            )

        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        grant_type = data.get("grant_type")
        code = data.get("code")
        scope = data.get("scope", "read")

        # Validate client credentials
        client = (
            request.env["akm.oauth.client"]
            .sudo()
            .search(
                [
                    ("client_id", "=", client_id),
                    ("client_secret", "=", client_secret),
                    ("is_active", "=", True),
                ],
                limit=1,
            )
        )
        if not client:
            return APIResponse.error(
                message="Invalid client credentials",
                error_code="INVALID_CLIENT",
                status_code=401,
            )

        # Handle authorization_code flow
        if grant_type == "authorization_code":
            if not code:
                return APIResponse.error(
                    message="Invalid or missing authorization code",
                    error_code="INVALID_GRANT",
                    status_code=400,
                )

            # Authcode model object
            AuthCode = request.env["akm.oauth.authcode"].sudo()
            auth_code_rec = AuthCode.search(
                [
                    ("code", "=", code),
                    ("client_id", "=", client.id),
                    ("used", "=", False),
                ],
                limit=1,
            )
            if not auth_code_rec or auth_code_rec.is_expired():
                return APIResponse.error(
                    message="Invalid or expired authorization code",
                    error_code="INVALID_GRANT",
                    status_code=400,
                )

            # Mark code used
            auth_code_rec.used = True

            # Validate Scope if it matches with client.scope
            if scope != client.scope:
                return APIResponse.error(
                    message=f"You are not allowed to request {scope}, allowed scope: {client.scope}",
                    error_code="INVALID_GRANT",
                    status_code=400,
                )

            # Create tokens
            token_obj = request.env["akm.oauth.token"].sudo()
            tokens = token_obj.create_token(
                client=client, user_name=auth_code_rec.user_name, scope=scope
            )

            # converr timedelta to seconds
            expires_in = ACCESS_TOKEN_EXPIRY.total_seconds()
            return APIResponse.success(
                data={
                    "access_token": tokens.access_token,
                    "refresh_token": tokens.refresh_token,
                    "token_type": "Bearer",
                    "expires_in": expires_in,
                }
            )

        # Handle refresh_token flow
        elif grant_type == "refresh_token":
            refresh_token = data.get("refresh_token")
            if not refresh_token:
                return APIResponse.error(
                    message="Missing refresh_token",
                    error_code="INVALID_REQUEST",
                    status_code=400,
                )

            # Validate refresh token
            token_record = (
                request.env["akm.oauth.token"]
                .sudo()
                .search(
                    [
                        ("refresh_token", "=", refresh_token),
                        ("client_id", "=", client.id),
                    ],
                    limit=1,
                )
            )

            if not token_record or not token_record.is_refresh_token_valid:
                return APIResponse.error(
                    message="Invalid or expired refresh token",
                    error_code="INVALID_GRANT",
                    status_code=400,
                )

            if not token_record.validate_refresh_token(
                refresh_token, client.client_secret
            ):
                return APIResponse.error(
                    message="Invalid refresh token",
                    error_code="INVALID_GRANT",
                    status_code=400,
                )

            try:
                new_token = token_record.rotate_refresh_token(token_record)
                access_token = new_token.access_token
                refresh_token = new_token.refresh_token
            except Exception as e:
                return APIResponse.error(
                    message=str(e),
                    error_code="TOKEN_ROTATION_FAILED",
                    status_code=500,
                )

            expires_in = ACCESS_TOKEN_EXPIRY.total_seconds()
            return APIResponse.success(
                data={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                    "expires_in": expires_in,
                }
            )

        # Default error if unknown grant_type
        return APIResponse.error(
            message="Unsupported grant_type",
            error_code="UNSUPPORTED_GRANT_TYPE",
            status_code=400,
        )
