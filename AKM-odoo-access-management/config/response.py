from typing import Any, Optional, Dict
from http import HTTPStatus
import json


class APIResponse:
    """
    A helper class to standardize API responses across the application.
    Provides consistent formatting for both success and error responses.
    """

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Operation successful",
        status_code: int = HTTPStatus.OK,
    ) -> Dict[str, Any]:
        """
        Creates a standardized success response.

        Args:
            data: The payload to return to the client
            message: A human-readable success message
            status_code: HTTP status code (defaults to 200 OK)

        Returns:
            A dictionary containing the standardized response
        """
        response = {
            "status": "success",
            "status_code": status_code,
            "message": message,
            "data": data,
        }
        return response

    @staticmethod
    def error(
        message: str = "An error occurred",
        error_code: Optional[str] = None,
        details: Optional[Any] = None,
        status_code: int = HTTPStatus.BAD_REQUEST,
    ) -> Dict[str, Any]:
        """
        Creates a standardized error response.

        Args:
            message: A human-readable error message
            error_code: A unique error identifier (e.g., "INVALID_CLIENT")
            details: Additional error details or validation errors
            status_code: HTTP status code (defaults to 400 Bad Request)

        Returns:
            A dictionary containing the standardized error response
        """
        response = {
            "status": "error",
            "status_code": status_code,
            "message": message,
            "error_code": error_code,
        }

        if details:
            response["details"] = details

        return response
