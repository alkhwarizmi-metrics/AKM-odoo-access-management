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

    accessible_models = fields.Many2many(
        "ir.model",
        "akm_client_model_rel",
        "client_id",
        "model_id",
        string="Accessible Models",
        domain=[("transient", "=", False)],  # Exclude transient models
        help="Models this client can access via API",
    )

    # One2many reverse references, take look into other models to understand
    token_ids = fields.One2many("akm.oauth.token", "client_id", string="Tokens")
    authcode_ids = fields.One2many(
        "akm.oauth.authcode", "client_id", string="Authorization Codes"
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

    model_count = fields.Integer(
        compute="_compute_model_count", string="Number of Accessible Models"
    )

    is_active = fields.Boolean(string="Active", default=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Override batch create to avoid deprecation warning."""
        for vals in vals_list:
            vals.setdefault("client_id", secrets.token_urlsafe(16))
            vals.setdefault("client_secret", secrets.token_urlsafe(32))
        return super().create(vals_list)

    @api.depends("accessible_models")
    def _compute_model_count(self):
        for record in self:
            record.model_count = len(record.accessible_models)

    def can_access_model(self, model_name):
        """Check if client can access a specific model"""
        self.ensure_one()
        return self.env["ir.model"].search(
            [("model", "=", model_name), ("id", "in", self.accessible_models.ids)],
            limit=1,
        )

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

    @api.depends("client_secret")
    def _compute_masked_client_secret(self):
        for record in self:
            if record.client_secret:
                visible_chars = 4  # Number of characters to show
                masked_length = len(record.client_secret) - visible_chars
                if masked_length > 0:
                    record.masked_client_secret = (
                        record.client_secret[:visible_chars] + "*" * masked_length
                    )
                else:
                    # If client_secret is shorter than or equal to visible_chars
                    record.masked_client_secret = record.client_secret
            else:
                record.masked_client_secret = ""
