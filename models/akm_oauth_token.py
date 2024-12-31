from odoo import models, fields, api
from typing import Optional
from ..config.managers import TokenManager
from ..config.constants import (
    ACCESS_TOKEN_EXPIRY,
    REFRESH_TOKEN_EXPIRY,
)
from ..config.utils import get_current_utc_datetime


class AkmOAuthToken(models.Model):
    _name = "akm.oauth.token"
    _description = "OAuth Access Tokens"

    access_token = fields.Char(readonly=True, copy=False)
    refresh_token = fields.Char(readonly=True, copy=False)
    client_id = fields.Many2one("akm.oauth.client", required=True, ondelete="cascade")
    user_name = fields.Char(string="User or System Name")

    # float field to store timestamp like 1735584083.268502
    expires_at = fields.Datetime(string="Expires At", required=True)
    scope = fields.Selection(
        [
            ("read", "Read only"),
            ("write", "Read and Write"),
            ("admin", "Admin"),
        ],
        string="Scope",
        required=True,
        default="read",
    )

    # Enables token revocation by the client and token rotation by application
    is_refresh_token_valid = fields.Boolean(
        string="Is Refresh Token Valid",
        default=True,
        help="Indicates whether the refresh token is still valid.",
    )

    @api.model
    def create_token(self, client, user_name: str, scope: Optional[str] = None):
        """
        Generate a new token for the user/client pair.

        Args:
            client (record): The OAuth client.
            user_name (str): The name of the user.
            scope (str, optional): The scope of the token.

        Returns:
            record: The created token record.
        """
        scope = scope or "read"

        # Define expiration times
        access_exp = get_current_utc_datetime() + ACCESS_TOKEN_EXPIRY
        refresh_exp = get_current_utc_datetime() + REFRESH_TOKEN_EXPIRY

        # Convert to naive datetime for Odoo storage
        naive_access_exp = access_exp.replace(tzinfo=None)

        # Payloads with unique identifier
        access_payload = {
            "client_id": client.id,
            "user_name": user_name,
            "scope": scope,
            "exp": access_exp.timestamp(),
        }
        access_payload = TokenManager.generate_unique_payload(access_payload)

        refresh_payload = {
            "client_id": client.id,
            "user_name": user_name,
            "scope": scope,
            "exp": refresh_exp.timestamp(),
        }
        refresh_payload = TokenManager.generate_unique_payload(refresh_payload)

        # Generate tokens using client_secret
        access_token = TokenManager.generate_token(access_payload, client.client_secret)
        refresh_token = TokenManager.generate_token(
            refresh_payload, client.client_secret
        )

        # Create token record
        token = self.create(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "client_id": client.id,
                "user_name": user_name,
                "expires_at": naive_access_exp,
                "scope": client.scope,
            }
        )

        return token

    def is_expired(self) -> bool:
        return get_current_utc_datetime() >= self.expires_at

    def validate_access_token(self, token: str, client_secret: str) -> bool:
        """
        Validate the access token.

        Args:
            token (str): The access token to validate.
            client_secret (str): The client's secret key.

        Returns:
            bool: True if valid, False otherwise.
        """
        if not TokenManager.validate_signature(token, client_secret):
            return False

        payload = TokenManager.decode_payload(token)
        if not payload:
            return False
        if get_current_utc_datetime().timestamp() > payload.get("exp", 0):
            return False
        return True

    def validate_refresh_token(self, token: str, client_secret: str) -> bool:
        """
        Validate the refresh token.

        Args:
            token (str): The refresh token to validate.
            client_secret (str): The client's secret key.

        Returns:
            bool: True if valid, False otherwise.
        """
        if not self.is_refresh_token_valid:
            return False
        if not TokenManager.validate_signature(token, client_secret):
            return False

        payload = TokenManager.decode_payload(token)
        if not payload:
            return False
        if get_current_utc_datetime().timestamp() > payload.get("exp", 0):
            return False
        return True

    @api.model
    def rotate_refresh_token(self, old_token_obj):
        """
        Rotate refresh token: invalidate the old and issue a new one.

        Args:
            old_token_obj (record): The old token record.

        Returns:
            record: The new token record.

        Raises:
            ValidationError: If the refresh token is invalid or already used.
        """
        if not old_token_obj.is_refresh_token_valid:
            raise models.ValidationError("Refresh token is invalid or already used.")

        # Invalidate the old refresh token
        old_token_obj.is_refresh_token_valid = False

        # Create a new token
        new_token = self.create_token(
            client=old_token_obj.client_id,
            user_name=old_token_obj.user_name,
            scope=old_token_obj.scope,
        )
        return new_token
