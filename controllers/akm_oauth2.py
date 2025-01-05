# addons/{MODULE_NAME}/controllers/akm_oauth2_controllers.py
from odoo import http
from odoo.http import request
from ..config.response import APIResponse
from ..config.constants import ACCESS_TOKEN_EXPIRY, API_PREFIX, MODULE_NAME
from ..config.utils import validate_http4_url
import secrets


class AkmOAuth2Controller(http.Controller):
    """
    OAuth2.0 Authentication Flow Controller

    Implements a standard OAuth2.0 authorization flow with the following endpoints:
    - /register: Client registration
    - /authorize: User authorization
    - /confirm: Consent confirmation
    - /token: Token exchange and refresh

    Security Features:
    - CSRF protection via state parameter
    - Client authentication
    """

    @http.route(
        f"{API_PREFIX}/register",
        type="json",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def register_client(self, **kwargs):
        """
        Register OAuth2.0 Client Application

        Registers a new client application and generates secure credentials.

        Request:
            {
                "name": "App Name",
                "redirect_uri": "https://app.example.com/callback"
            }

        Response:
            {
                "client_id": "generated_id",
                "client_secret": "generated_secret",
                "name": "App Name",
                "redirect_uri": "https://app.example.com/callback"
            }

        Errors:
            - INVALID_REQUEST: Missing or invalid parameters
        """

        # Get parameters from JSONRPC params
        params = kwargs

        name = params.get("name")
        redirect_uri = params.get("redirect_uri")

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
        Authorization Request Handler

        Validates the authorization request and displays consent screen.

        Parameters:
            - client_id: Client application identifier
            - response_type: Must be "code"
            - scope: Requested permissions (default: "read")
            - state: Anti-CSRF token

        Returns:
            - Renders consent screen on success
            - Error message on validation failure
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
            f"{MODULE_NAME}.akm_oauth_consent_form",
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
        User Consent Handler

        Processes user's consent decision and redirects with appropriate response.

        Parameters:
            - decision: "allow" or "deny"
            - client_id: Client identifier
            - state: Anti-CSRF token
            - scope: Requested scope

        Returns:
            Redirects to client's redirect_uri with either:
            - Success: ?code=auth_code&state=xyz
            - Denial: ?error=access_denied&state=xyz
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
        elif decision == "deny":
            try:
                # Handle denial
                separator = "&" if "?" in redirect_uri else "?"
                final_uri = (
                    f"{redirect_uri}{separator}error=access_denied&state={state}"
                )

                return request.make_response(
                    "",
                    headers={"Location": final_uri, "Cache-Control": "no-cache"},
                    status=302,
                )
            except Exception as e:
                # Log the exception
                request.env.cr.commit()  # Commit the transaction if needed
                return "Error processing denial."
        else:
            return "Invalid decision parameter."

    @http.route(
        f"{API_PREFIX}/token", type="json", auth="none", methods=["POST"], csrf=False
    )
    def token(self, **kwargs):
        """
        Token Exchange Handler

        Supports authorization_code and refresh_token grant types.

        Grant Types:
            1. authorization_code:
               Request:
                   {
                       "grant_type": "authorization_code",
                       "client_id": "id",
                       "client_secret": "secret",
                       "code": "auth_code"
                   }

            2. refresh_token:
               Request:
                   {
                       "grant_type": "refresh_token",
                       "client_id": "id",
                       "client_secret": "secret",
                       "refresh_token": "token"
                   }

        Response:
            {
                "access_token": "new_token",
                "refresh_token": "new_refresh_token",
                "token_type": "Bearer",
                "expires_in": 3600
            }

        Errors:
            - INVALID_CLIENT: Invalid credentials
            - INVALID_GRANT: Invalid/expired code or token
            - UNSUPPORTED_GRANT_TYPE: Invalid grant_type
        """

        params = kwargs

        client_id = params.get("client_id")
        client_secret = params.get("client_secret")
        grant_type = params.get("grant_type")
        code = params.get("code")
        scope = params.get("scope", "read")

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
            refresh_token = params.get("refresh_token")
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
