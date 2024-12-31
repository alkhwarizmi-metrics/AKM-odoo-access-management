from odoo import models, fields, api
from ..config.utils import validate_http4_url
import secrets


class AkmOAuthClient(models.Model):
    _name = "akm.oauth.client"
    _description = "OAuth Client"

    depends = ["base"]

    name = fields.Char(required=True)
    client_id = fields.Char(readonly=True, copy=False)
    client_secret = fields.Char(readonly=True, copy=False)
    redirect_uri = fields.Char(string="Redirect URI", required=True)

    permission_ids = fields.One2many(
        "akm.client.permission", "client_id", string="Model Permissions"
    )

    # One2many reverse references, take look into other models to understand
    token_ids = fields.One2many("akm.oauth.token", "client_id", string="Tokens")
    authcode_ids = fields.One2many(
        "akm.oauth.authcode", "client_id", string="Authorization Codes"
    )
    request_log_ids = fields.One2many(
        "akm.request.log", "client_id", string="Request Logs"
    )

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

    is_active = fields.Boolean(string="Active", default=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Override batch create to avoid deprecation warning."""
        for vals in vals_list:
            vals.setdefault("client_id", secrets.token_urlsafe(16))
            vals.setdefault("client_secret", secrets.token_urlsafe(32))
        return super().create(vals_list)

    def can_access_model(self, model_name):
        """
        Now search in 'akm.client.permission' to see if the client has permission for the given model_name.
        """
        self.ensure_one()
        permission = self.env["akm.client.permission"].search(
            [
                ("client_id", "=", self.id),
                ("model_id.model", "=", model_name),
            ],
            limit=1,
        )
        return bool(permission)

    def can_access_field(self, model_name, field_name):
        """
        Extended check to validate if field-level permission is also granted.
        """

        if field_name in ["id", "create_date", "write_date"]:  # Add essential fields
            return True

        self.ensure_one()
        permission = self.env["akm.client.permission"].search(
            [
                ("client_id", "=", self.id),
                ("model_id.model", "=", model_name),
            ],
            limit=1,
        )

        if not permission:
            return False
        if not permission.field_ids:
            return False
        return field_name in permission.field_ids.mapped("name")

    @api.constrains("redirect_uri")
    def _check_redirect_uri(self):
        """Validate redirect URI format and security"""
        for record in self:
            if not record.redirect_uri:
                continue
            if not validate_http4_url(record.redirect_uri):
                raise models.ValidationError(
                    "Redirect URI must be a valid HTTP/HTTPS URL"
                )
