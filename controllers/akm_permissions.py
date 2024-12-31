from odoo import http, fields
from odoo.http import request
from ..config.response import APIResponse
from ..config.constants import API_PREFIX
from ..config.decorators import require_authenticated_client
import logging

_logger = logging.getLogger(__name__)


class AkmPermissionsController(http.Controller):

    @http.route(
        f"{API_PREFIX}/permissions",
        type="json",  # Ensure the route type is "json"
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    @require_authenticated_client
    def get_permissions(self, **kwargs):
        """
        Retrieve List of accessible models and fields.
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

        permissions = client.permission_ids
        if not permissions:
            return APIResponse.error(
                message=f"No model permissions found for client '{client.name}'",
                error_code="NO_ACCESSIBLE_MODELS",
                status_code=404,
                details={"client_id": client.client_id, "scope": client.scope},
            )

        models_info = []
        for permission in permissions:
            model = permission.model_id.model
            model_name = permission.model_id.name

            try:
                # Get all fields info first
                model_fields = request.env[model].sudo().fields_get()

                # Filter only permitted fields
                permitted_field_names = permission.field_ids.mapped("name")

                fields_info = []
                for field_name in permitted_field_names:
                    if field_name in model_fields:
                        field_attrs = model_fields[field_name]
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
                        "model_description": model_name,
                        "fields": fields_info,
                    }
                )

            except Exception as e:
                _logger.error(f"Error fetching fields for model '{model}': {e}")
                return APIResponse.error(
                    message="Error fetching model fields",
                    error_code="FIELD_FETCH_ERROR",
                    status_code=500,
                )

        return APIResponse.success(data=models_info)
