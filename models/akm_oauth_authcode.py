from odoo import models, fields, api
import secrets
from datetime import datetime, timedelta


class AkmOAuthAuthCode(models.Model):
    _name = "akm.oauth.authcode"
    _description = "OAuth Authorization Code"

    # Authorization code is short-lived (5 minutes)
    # Can only be used once
    # Must be exchanged with client_secret
    # Separation of concerns between authorization and token issuance

    code = fields.Char(readonly=True, copy=False)
    client_id = fields.Many2one("akm.oauth.client", required=True, ondelete="cascade")
    user_name = fields.Char(string="User or System Name")
    expires_at = fields.Datetime()
    used = fields.Boolean(default=False, readonly=True)

    @api.model
    def create_code(self, client_id, user_name):
        """Helper method: generate a code entry with short expiration."""
        code = secrets.token_urlsafe(16)
        return self.create(
            {
                "code": code,
                "client_id": client_id.id,
                "user_name": user_name,
                "expires_at": datetime.now() + timedelta(minutes=5),
            }
        )

    def is_expired(self):
        return fields.Datetime.now() >= self.expires_at

    def verify_and_use(self, code, client):
        """Verify and consume the authorization code"""
        self.ensure_one()
        if (
            self.code == code
            and self.client_id == client
            and not self.used
            and not self.is_expired()
        ):
            self.used = True
            return True
        return False
