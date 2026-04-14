from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os

import jwt

from app.core.config import settings


class InvalidTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200_000,
    )
    return f"{base64.b64encode(salt).decode('ascii')}${base64.b64encode(password_hash).decode('ascii')}"


def verify_password(password: str, stored_password_hash: str) -> bool:
    try:
        salt_encoded, hash_encoded = stored_password_hash.split("$", 1)
        salt = base64.b64decode(salt_encoded.encode("ascii"))
        expected_hash = base64.b64decode(hash_encoded.encode("ascii"))
    except (ValueError, UnicodeDecodeError):
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200_000,
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def create_access_token(
    *,
    subject: str,
    role: str,
    expires_minutes: int | None = None,
) -> str:
    expire_delta = timedelta(
        minutes=expires_minutes
        if expires_minutes is not None
        else settings.access_token_expire_minutes,
    )
    payload = {
        "sub": subject,
        "role": role,
        "exp": datetime.now(timezone.utc) + expire_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, str]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.InvalidTokenError as error:
        raise InvalidTokenError("Invalid or expired access token.") from error

    subject = payload.get("sub")
    role = payload.get("role")

    if not isinstance(subject, str) or not isinstance(role, str):
        raise InvalidTokenError("Access token payload is missing required claims.")

    return {"sub": subject, "role": role}
