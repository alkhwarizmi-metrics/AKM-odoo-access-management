import secrets
import json
import base64
import hmac
import hashlib
from typing import Optional, Dict
from datetime import datetime, timezone
from odoo import models


class TokenManager:
    """
    A utility class for generating and validating JWT-like tokens.
    """

    @staticmethod
    def encode_payload(payload: Dict) -> str:
        """
        Encode the payload to a base64 string.

        Args:
            payload (dict): The data to encode.

        Returns:
            str: The base64-encoded payload.
        """
        payload_json = json.dumps(payload).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
        return payload_b64

    @staticmethod
    def decode_payload(token: str) -> Optional[Dict]:
        """
        Decode the base64 token back to a dictionary.

        Args:
            token (str): The JWT-like token.

        Returns:
            dict or None: The decoded payload or None if decoding fails.
        """
        try:
            _, payload_b64, _ = token.split(".")
            padding = "=" * (-len(payload_b64) % 4)  # Add necessary padding
            payload_json = base64.urlsafe_b64decode(payload_b64 + padding).decode(
                "utf-8"
            )
            payload = json.loads(payload_json)
            return payload
        except (base64.binascii.Error, json.JSONDecodeError, ValueError):
            return None

    @staticmethod
    def generate_signature(client_secret: str, payload_b64: str) -> str:
        """
        Generate an HMAC-SHA256 signature using the client_secret.

        Args:
            client_secret (str): The secret key used for signing.
            payload_b64 (str): The base64-encoded payload.

        Returns:
            str: The generated signature.
        """
        signature = hmac.new(
            key=client_secret.encode("utf-8"),
            msg=payload_b64.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        return signature_b64

    @staticmethod
    def generate_token(payload: Dict, client_secret: str) -> str:
        """
        Generate a JWT-like token.

        Args:
            payload (dict): The payload data.
            client_secret (str): The secret key used for signing.

        Returns:
            str: The generated token.
        """
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = TokenManager.encode_payload(header)
        payload_b64 = TokenManager.encode_payload(payload)
        signature = TokenManager.generate_signature(client_secret, payload_b64)
        token = f"{header_b64}.{payload_b64}.{signature}"
        return token

    @staticmethod
    def validate_signature(token: str, client_secret: str) -> bool:
        """
        Validate the token's signature.

        Args:
            token (str): The token to validate.
            client_secret (str): The secret key used for signing.

        Returns:
            bool: True if signature is valid, False otherwise.
        """
        try:
            _, payload_b64, signature = token.split(".")
            expected_signature = TokenManager.generate_signature(
                client_secret, payload_b64
            )
            return hmac.compare_digest(signature, expected_signature)
        except ValueError:
            return False

    @staticmethod
    def generate_unique_payload(payload: Dict) -> Dict:
        """
        Generate a unique payload by adding a unique identifier.

        Args:
            payload (dict): The original payload.

        Returns:
            dict: The payload with a unique identifier added.
        """
        payload_copy = payload.copy()
        payload_copy["jti"] = secrets.token_urlsafe(16)  # JWT ID for uniqueness
        payload_copy["iat"] = datetime.now(timezone.utc).timestamp()  # Issued at
        return payload_copy

    @staticmethod
    def get_token_record(token: str, env) -> Optional[models.Model]:
        """
        Retrieve the token record from the database.

        Args:
            token (str): The access or refresh token.
            env: Odoo environment.

        Returns:
            record or None: The token record if found, else None.
        """
        token_record = (
            env["akm.oauth.token"]
            .sudo()
            .search(
                ["|", ("access_token", "=", token), ("refresh_token", "=", token)],
                limit=1,
            )
        )
        return token_record

    @staticmethod
    def is_client_active(client_id: int, env) -> bool:
        """
        Check if the client associated with the given client_id is active.
        """
        client = (
            env["akm.oauth.client"].sudo().search([("id", "=", client_id)], limit=1)
        )
        return client.exists() and client.is_active
