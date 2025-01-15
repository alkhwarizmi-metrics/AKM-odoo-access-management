import os
from datetime import timedelta

MODULE_NAME = os.path.basename(os.path.dirname(os.path.dirname(__file__)))
API_VERSION = "v1"
API_PREFIX = f"/{MODULE_NAME}/{API_VERSION}"

ACCESS_TOKEN_EXPIRY = timedelta(hours=1)
REFRESH_TOKEN_EXPIRY = timedelta(days=30)
