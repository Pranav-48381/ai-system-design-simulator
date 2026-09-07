"""System Design Interview Simulator - Security & Cryptographic Utilities.

Provides secure token generation, HMAC-SHA256 signature verification, password hashing
using PBKDF2, and temporary WebSocket ticket issuance.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.core.config import settings
from app.core.exceptions import AuthenticationError

PBKDF2_ITERATIONS = 600_000
SALT_SIZE_BYTES = 16


def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 with a cryptographically secure salt."""
    salt = secrets.token_bytes(SALT_SIZE_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    key_b64 = base64.b64encode(derived_key).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_b64}${key_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2-HMAC-SHA256 hash string."""
    try:
        algorithm, iterations_str, salt_b64, key_b64 = hashed_password.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_key = base64.b64decode(key_b64.encode("ascii"))
        derived_key = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(derived_key, expected_key)
    except Exception:
        return False


def generate_random_token(length_bytes: int = 32) -> str:
    """Generate a URL-safe random string for API keys or one-time session tokens."""
    return secrets.token_urlsafe(length_bytes)


def create_signed_token(
    payload: dict[str, Any],
    secret_key: str | None = None,
    expires_in_seconds: int = 86400,
) -> str:
    """Generate an HMAC-SHA256 signed payload containing an expiration timestamp."""
    secret = (secret_key or settings.SECRET_KEY).encode("utf-8")
    token_payload = {
        **payload,
        "exp": int(time.time()) + expires_in_seconds,
        "iat": int(time.time()),
    }
    payload_json = json.dumps(token_payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("ascii")

    signature = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("ascii")
    return f"{payload_b64}.{sig_b64}"


def verify_signed_token(
    token: str,
    secret_key: str | None = None,
) -> dict[str, Any]:
    """Verify HMAC-SHA256 signature and expiration of a signed token string."""
    secret = (secret_key or settings.SECRET_KEY).encode("utf-8")
    try:
        payload_b64, sig_b64 = token.split(".")
        expected_sig = hmac.new(
            secret, payload_b64.encode("ascii"), hashlib.sha256
        ).digest()
        provided_sig = base64.urlsafe_b64decode(sig_b64.encode("ascii"))

        if not hmac.compare_digest(expected_sig, provided_sig):
            raise AuthenticationError("Invalid token signature.")

        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
        payload: dict[str, Any] = json.loads(payload_bytes.decode("utf-8"))

        if "exp" in payload and payload["exp"] < time.time():
            raise AuthenticationError("Token has expired.")

        return payload
    except AuthenticationError:
        raise
    except Exception as exc:
        raise AuthenticationError(f"Malformed token: {str(exc)}") from exc


def generate_ws_ticket(session_id: str, user_id: str) -> str:
    """Generate a short-lived ticket for WebSocket connection authorization (60s validity)."""
    return create_signed_token(
        {"sub": user_id, "session_id": session_id, "type": "ws_ticket"},
        expires_in_seconds=60,
    )


def verify_ws_ticket(ticket: str, expected_session_id: str) -> str:
    """Verify a WebSocket ticket and assert it matches the session ID. Returns user_id."""
    payload = verify_signed_token(ticket)
    if payload.get("type") != "ws_ticket":
        raise AuthenticationError("Invalid ticket type.")
    if payload.get("session_id") != expected_session_id:
        raise AuthenticationError("Ticket session ID does not match target session.")
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Ticket missing subject identifier.")
    return str(user_id)
