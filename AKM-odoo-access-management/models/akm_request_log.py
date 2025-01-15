from odoo import models, fields, api


class AkmRequestLog(models.Model):
    _name = "akm.request.log"
    _description = "API Request Log"
    _order = "create_date desc"

    depends = ["base"]

    name = fields.Char(compute="_compute_name", store=True)
    client_id = fields.Many2one(
        "akm.oauth.client", string="OAuth Client", ondelete="set null"
    )
    endpoint = fields.Char(required=True)
    method = fields.Char(required=True)
    request_params = fields.Text()
    status_code = fields.Integer()
    ip_address = fields.Char()
    user_agent = fields.Char()
    duration = fields.Float(help="Request duration in seconds")

    @api.depends("endpoint", "create_date")
    def _compute_name(self):
        for record in self:
            record.name = f"{record.endpoint} ({record.create_date})"
