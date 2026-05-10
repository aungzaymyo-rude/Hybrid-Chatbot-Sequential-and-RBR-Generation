from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets


PBKDF2_ROUNDS = 120_000


@dataclass
class AuthenticatedAdmin:
    user_id: int
    username: str
    must_change_password: bool


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt_hex = salt_hex or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        bytes.fromhex(salt_hex),
        PBKDF2_ROUNDS,
    )
    return salt_hex, digest.hex()


def verify_password(password: str, salt_hex: str, password_hash: str) -> bool:
    _, candidate = hash_password(password, salt_hex=salt_hex)
    return secrets.compare_digest(candidate, password_hash)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def session_expiry(hours: int) -> datetime:
    return utc_now() + timedelta(hours=hours)
