from odoo import http
from odoo.http import request
from odoo.models import Model
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple, Literal

from ..config.response import APIResponse
from ..config.pagination import Pagination
from ..config.constants import API_PREFIX
from ..config.decorators import require_authenticated_client, log_request


DomainOperator = Literal["=", ">=", "<="]
DomainTuple = Tuple[str, DomainOperator, Any]
Domain = List[DomainTuple]
JsonDict = Dict[str, Any]

_logger = logging.getLogger(__name__)


class AkmRecordsController(http.Controller):
    @http.route(
        f"{API_PREFIX}/records", type="json", auth="none", methods=["GET"], csrf=False
    )
    @log_request
    @require_authenticated_client
    def get(self, **kwargs: Dict[str, Any]) -> JsonDict:
        """Read records from a given model with pagination and filters."""
        client: Optional[Model] = kwargs.get("client")

        # Validate client
        if error := self._validate_client(client):
            return error

        # Get parameters from JSONRPC params
        params = kwargs

        # copy kwargs to self to use in log_request
        self.kwargs = kwargs
        model_name = params.get("model_name")

        if error := self._validate_model_access(client, model_name):

            return error

        # Validate datetime params and build domain
        error, domain = self._validate_datetime_params(
            client,
            model_name,
            params.get("date_time_gte"),
            params.get("date_time_lte"),
            params.get("targetted_datetime_field"),
        )
        if error:
            return error

        # Handle pagination
        page = int(params.get("page", 1))
        per_page = int(params.get("per_page", 10))
        paginator = Pagination(page=page, per_page=per_page)

        try:
            ModelObj = request.env[model_name].sudo()
            records = ModelObj.search(domain)
            paginated_records = paginator.paginate(records)
        except Exception as e:
            _logger.error(f"Error reading data: {e}")

            return APIResponse.error(
                message="Error fetching records",
                error_code="READ_ERROR",
                status_code=500,
            )

        # Get permitted fields
        error, field_list = self._get_permitted_fields(
            client, model_name, kwargs.get("fields", "*")
        )
        if error:
            return error

        # Read records with permitted fields
        res_data = [rec.read(field_list)[0] for rec in paginated_records]
        pagination_info = paginator.to_response(records_count=len(records))

        return APIResponse.success(
            data={
                "records": res_data,
                "pagination": pagination_info,
            }
        )

    def _validate_datetime(self, date_str: str) -> bool:
        """Validate datetime string format."""
        try:
            datetime.strptime(date_str, DEFAULT_SERVER_DATETIME_FORMAT)
            return True
        except ValueError:
            return False

    def _validate_client(self, client: Optional[Model]) -> Optional[JsonDict]:
        """Validate client and its scope."""
        if not client:

            return APIResponse.error(
                message="Client not found",
                error_code="INVALID_CLIENT",
                status_code=401,
            )

        if client.scope not in ("read", "write", "admin"):
            return APIResponse.error(
                message="Client scope invalid",
                error_code="INVALID_SCOPE",
                status_code=403,
            )
        return None

    def _validate_model_access(
        self, client: Model, model_name: Optional[str]
    ) -> Optional[JsonDict]:
        """Validate model name and access."""
        if not model_name:
            return APIResponse.error(
                message="No model_name provided",
                error_code="MISSING_PARAMETER",
                status_code=400,
            )

        if not client.can_access_model(model_name):
            return APIResponse.error(
                message=f"Model '{model_name}' not accessible for this client",
                error_code="ACCESS_DENIED",
                status_code=403,
            )
        return None

    def _validate_datetime_params(
        self,
        client: Model,
        model_name: str,
        date_time_gte: Optional[str],
        date_time_lte: Optional[str],
        targetted_datetime_field: Optional[str],
    ) -> Tuple[Optional[JsonDict], Optional[Domain]]:
        """Validate datetime parameters and return domain if valid."""
        domain = []

        if any([date_time_gte, date_time_lte]) and not all(
            [date_time_gte, date_time_lte, targetted_datetime_field]
        ):
            return (
                APIResponse.error(
                    message="All datetime parameters must be provided together",
                    error_code="INVALID_DATETIME_PARAMS",
                    status_code=400,
                ),
                None,
            )

        if date_time_gte and date_time_lte:
            if not self._validate_datetime(
                date_time_gte
            ) or not self._validate_datetime(date_time_lte):
                return (
                    APIResponse.error(
                        message=f"Datetime must be in format: {DEFAULT_SERVER_DATETIME_FORMAT}",
                        error_code="INVALID_DATETIME_FORMAT",
                        status_code=400,
                    ),
                    None,
                )

            ModelObj: Model = request.env[model_name].sudo()
            fields_info = ModelObj.fields_get([targetted_datetime_field])

            if not fields_info.get(targetted_datetime_field):
                return (
                    APIResponse.error(
                        message=f"Field '{targetted_datetime_field}' does not exist",
                        error_code="FIELD_NOT_FOUND",
                        status_code=400,
                    ),
                    None,
                )

            if fields_info[targetted_datetime_field]["type"] != "datetime":
                return (
                    APIResponse.error(
                        message=f"Field '{targetted_datetime_field}' must be datetime",
                        error_code="INVALID_FIELD_TYPE",
                        status_code=400,
                    ),
                    None,
                )

            if not client.can_access_field(model_name, targetted_datetime_field):
                return (
                    APIResponse.error(
                        message=f"Field '{targetted_datetime_field}' not accessible",
                        error_code="FIELD_ACCESS_DENIED",
                        status_code=403,
                    ),
                    None,
                )

            domain.extend(
                [
                    (targetted_datetime_field, ">=", date_time_gte),
                    (targetted_datetime_field, "<=", date_time_lte),
                ]
            )

        return None, domain

    def _get_permitted_fields(
        self, client: Model, model_name: str, fields_param: str
    ) -> Tuple[Optional[JsonDict], Optional[List[str]]]:
        """Get and validate permitted fields."""
        field_list = []

        if fields_param == "*":
            permission = client.permission_ids.filtered(
                lambda p: p.model_id.model == model_name
            )
            if not permission:
                return (
                    APIResponse.error(
                        message=f"No field permissions found for model '{model_name}'",
                        error_code="NO_FIELD_PERMISSIONS",
                        status_code=403,
                    ),
                    None,
                )
            field_list = permission.field_ids.mapped("name")
        else:
            field_list = [f.strip() for f in fields_param.split(",") if f.strip()]
            for field in field_list:
                if not client.can_access_field(model_name, field):
                    return (
                        APIResponse.error(
                            message=f"Field '{field}' not accessible",
                            error_code="FIELD_ACCESS_DENIED",
                            status_code=403,
                        ),
                        None,
                    )

        if "id" not in field_list:
            field_list.append("id")

        return None, field_list
