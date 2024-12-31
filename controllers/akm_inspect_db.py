from odoo import http, fields
from odoo.http import request
from ..config.response import APIResponse
from ..config.constants import API_PREFIX
from ..config.decorators import require_authenticated_client
import logging

_logger = logging.getLogger(__name__)


class AkmInspectAccessibleDataController(http.Controller):

    @http.route(
        f"{API_PREFIX}/inspect-accessible-models",
        type="json",  # Ensure the route type is "json"
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    @require_authenticated_client
    def inspect_accessible_models(self, **kwargs):
        """
        Inspect accessible database models for the authenticated client.
        - Validates access token and retrieves client_id.
        - Fetches accessible models and their fields.
        - Returns model details in JSON format.
        """

        client = kwargs.get("client")
        if not client:
            return APIResponse.error(
                message="Client not found",
                error_code="INVALID_CLIENT",
                status_code=401,
            )

        accessible_models = (
            client.accessible_models
        )  # Assuming this is a Many2many field

        if not accessible_models:
            return APIResponse.error(
                message="No accessible models found for the client",
                error_code="NO_ACCESSIBLE_MODELS",
                status_code=404,
            )

        models_info = []
        for model_rel in accessible_models:
            model = model_rel.model  # Technical model name
            model_description = model_rel.name  # Human-readable model name

            try:
                # Ensure valid user context and use sudo() for elevated access
                model_fields = request.env[model].sudo().fields_get()
            except Exception as e:
                _logger.error(f"Error fetching fields for model '{model}': {e}")
                continue  # Skip this model if there's an error

            fields_info = []
            for field_name, field_attrs in model_fields.items():
                fields_info.append(
                    {
                        "name": field_name,
                        "type": field_attrs.get("type"),
                        "required": field_attrs.get("required", False),
                        "readonly": field_attrs.get("readonly", False),
                        "string": field_attrs.get("string"),
                    }
                )

            models_info.append(
                {
                    "model_name": model,
                    "model_description": model_description,
                    "fields": fields_info,
                }
            )

        return APIResponse.success(data={"accessible_models": models_info})
