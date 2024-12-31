from odoo import http, fields
from odoo.http import request
from odoo.models import Model
from ..config.response import APIResponse
from ..config.pagination import Pagination
from ..config.constants import API_PREFIX
from ..config.decorators import require_authenticated_client
import logging
from typing import List, Dict, Optional, Any, Tuple, Literal

# Custom type definitions
DomainOperator = Literal[
    "=", "!=", ">", ">=", "<", "<=", "like", "ilike", "in", "not in", "=ilike"
]
DomainTuple = Tuple[str, DomainOperator, Any]
Domain = List[DomainTuple]
JsonDict = Dict[str, Any]

_logger = logging.getLogger(__name__)


class AkmDataController(http.Controller):
    @http.route(
        f"{API_PREFIX}/data/read",
        type="json",
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    @require_authenticated_client
    def read_data(self, **kwargs: Dict[str, Any]) -> JsonDict:
        """
        Read records from a given model with filtering and pagination.

        Args:
            **kwargs: Dictionary containing query parameters
                - model_name: str
                - fields: str (comma-separated or "*")
                - page: int
                - per_page: int
                - filter_by_*: str
                - filter_lookup_*: str
                - date_time_gte: str
                - date_time_lte: str
                - date_gte: str
                - date_lte: str

        Returns:
            JsonDict: API response containing records and pagination info
        """

        client: Optional[Model] = kwargs.get("client")
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

        model_name: Optional[str] = kwargs.get("model_name")
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

        # Check if model is accessible
        if not client.can_access_model(model_name):
            return APIResponse.error(
                message=f"Model '{model_name}' not accessible for this client",
                error_code="ACCESS_DENIED",
                status_code=403,
            )

        # Build domain based on query params
        domain: Domain = []

        # DateTime range filtering
        date_time_gte: Optional[str] = kwargs.get("date_time_gte")
        date_time_lte: Optional[str] = kwargs.get("date_time_lte")
        targetted_datetime_field: Optional[str] = kwargs.get("targetted_datetime_field")

        if all([date_time_gte, date_time_lte, targetted_datetime_field]):
            domain.extend(
                [
                    (targetted_datetime_field, ">=", date_time_gte),
                    (targetted_datetime_field, "<=", date_time_lte),
                ]
            )

        # Date range filtering
        date_gte: Optional[str] = kwargs.get("date_gte")
        date_lte: Optional[str] = kwargs.get("date_lte")
        targetted_date_field: Optional[str] = kwargs.get("targetted_date_field")

        if all([date_gte, date_lte, targetted_date_field]):
            domain.extend(
                [
                    (targetted_date_field, ">=", date_gte),
                    (targetted_date_field, "<=", date_lte),
                ]
            )

        # Generic field filters
        for key, value in kwargs.items():
            if key.startswith("filter_by_"):
                field_name: str = key.replace("filter_by_", "")
                lookup_type: str = kwargs.get(f"filter_lookup_{field_name}", "=")

                if lookup_type == "startswith":
                    domain.append((field_name, "=ilike", f"{value}%"))
                elif lookup_type == "endswith":
                    domain.append((field_name, "=ilike", f"%{value}"))
                elif lookup_type == "in":
                    values_list: List[str] = [v.strip() for v in str(value).split(",")]
                    domain.append((field_name, "in", values_list))
                else:
                    domain.append((field_name, "ilike", value))

        page: int = int(kwargs.get("page", 1))
        per_page: int = int(kwargs.get("per_page", 10))
        paginator: Pagination = Pagination(page=page, per_page=per_page)

        try:
            ModelObj: Model = request.env[model_name].sudo()
            records: Model = ModelObj.search(domain)
            paginated_records: Model = paginator.paginate(records)
        except Exception as e:
            _logger.error(f"Error reading data from model '{model_name}': {e}")
            return APIResponse.error(
                message="Error fetching records",
                error_code="READ_ERROR",
                status_code=500,
            )

        fields_param: str = kwargs.get("fields", "")
        if fields_param == "*":
            res_data: List[Dict[str, Any]] = [
                rec.read()[0] for rec in paginated_records
            ]
        else:
            field_list: List[str] = [
                f.strip() for f in fields_param.split(",") if f.strip()
            ]
            if not field_list:
                res_data = [
                    {"id": rec.id, "name": rec.display_name}
                    for rec in paginated_records
                ]
            else:
                if "id" not in field_list:
                    field_list.append("id")
                res_data = [rec.read(field_list)[0] for rec in paginated_records]

        pagination_info: Dict[str, int] = paginator.to_response(
            records_count=len(records)
        )

        return APIResponse.success(
            data={
                "records": res_data,
                "pagination": pagination_info,
            }
        )

    @http.route(
        f"{API_PREFIX}/data/write",
        type="json",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    @require_authenticated_client
    def write_data(self, **kwargs: Dict[str, Any]) -> JsonDict:
        """Placeholder for write operations."""
        return APIResponse.success(
            data={"message": "Write functionality not yet implemented"}
        )
