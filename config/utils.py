from datetime import datetime, timezone
from odoo import models
from typing import Any


def get_current_utc_datetime():
    return datetime.now(timezone.utc)


def validate_http4_url(url: str) -> bool:
    """
    Validate the given URL.

    Args:
        url (str): The URL to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    try:
        from urllib.parse import urlparse

        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def make_serializable(obj: Any) -> Any:
    """
    Recursively convert objects to serializable formats.

    Args:
        obj (Any): The object to serialize.

    Returns:
        Any: A JSON-serializable representation of the object.
    """
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, models.Model):
        return str(obj)  # or obj.id if preferred
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)
