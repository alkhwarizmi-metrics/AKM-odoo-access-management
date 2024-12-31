from datetime import datetime, timezone


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
