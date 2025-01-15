from odoo import http
from odoo.http import request
from ..config.response import APIResponse
from ..config.constants import API_PREFIX
from ..config.decorators import require_authenticated_client, log_request


class AkmPermissionsController(http.Controller):
    """
    Permissions Management Controller for OAuth2.0 API Access

    Provides endpoints to retrieve and validate client permissions for:
    - Accessible Odoo models
    - Permitted fields within models
    - Access level details

    Security Features:
    - Requires valid OAuth2.0 token
    - Field-level access control
    - Model-level permissions
    """

    @http.route(
        f"{API_PREFIX}/permissions",
        type="json",  # Ensure the route type is "json"
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    @log_request
    @require_authenticated_client
    def get_permissions(self, **kwargs):
        """
        Retrieve Authorized Model Permissions

        Returns detailed information about models and fields that the authenticated
        client has permission to access.

        Request:
            Headers:
                Authorization: Bearer <token>

        Response:
            {
                "status": "success",
                "data": [
                    {
                        "model_name": "res.partner",
                        "model_description": "Contact",
                        "fields": [
                            {
                                "name": "name",
                                "type": "char",
                                "required": true,
                                "readonly": false,
                                "string": "Name"
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }

        Errors:
            - INVALID_CLIENT (401): Client not found or invalid
            - NO_ACCESSIBLE_MODELS (404): No permissions configured
            - FIELD_FETCH_ERROR (500): Error retrieving field information
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
                details={
                    "client_id": client.client_id,
                    "scope": client.scope,
                    "help": "Contact administrator to configure model permissions",
                },
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
                                "relation": field_attrs.get("relation"),
                                "selection": field_attrs.get("selection"),
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

                return APIResponse.error(
                    message="Error fetching model fields",
                    error_code="FIELD_FETCH_ERROR",
                    status_code=500,
                )

        return APIResponse.success(data=models_info)
