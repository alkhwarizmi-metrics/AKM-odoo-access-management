from odoo import models, fields


class AkmClientPermission(models.Model):
    """
    Stores which models and fields a client can access.
    This replaces the Many2many accessible_models field.
    """

    _name = "akm.client.permission"
    _description = "Client Model & Field Permissions"

    client_id = fields.Many2one(
        "akm.oauth.client",
        required=True,
        ondelete="cascade",
        string="OAuth Client",
    )

    model_id = fields.Many2one(
        "ir.model",
        required=True,
        ondelete="cascade",
        string="Model",
        domain=[("transient", "=", False)],
    )

    field_ids = fields.Many2many(
        "ir.model.fields",  # comodel_name
        "akm_permission_field_rel",  # relation (table name)
        "permission_id",  # column1 (this model)
        "field_id",  # column2 (target model)
        string="Accessible Fields",
        domain="[('model_id', '=', model_id), ('store', '=', True)]",  # Only stored fields
    )

    _sql_constraints = [
        (
            "unique_client_model",
            "unique(client_id, model_id)",
            "Client-Model combination must be unique.",
        )
    ]
