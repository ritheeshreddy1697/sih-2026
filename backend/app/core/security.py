from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hasher = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hasher.hash("not-a-real-account-password")


class TokenValidationError(Exception):
    pass


@dataclass(frozen=True)
class TokenPayload:
    subject: UUID
    session_id: UUID
    token_type: str


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password, password_hash)
    except Exception:
        return False


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _create_jwt(subject: UUID, session_id: UUID, token_type: str, expires_at: datetime) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "sid": str(session_id),
        "jti": str(uuid4()),
        "type": token_type,
        "iat": now,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: UUID, session_id: UUID) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return _create_jwt(subject, session_id, "access", expires_at), expires_at


def create_refresh_token(subject: UUID, session_id: UUID) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return _create_jwt(subject, session_id, "refresh", expires_at), expires_at


def decode_token(token: str, expected_type: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=30,
            options={"require": ["sub", "sid", "jti", "type", "iat", "exp", "iss", "aud"]},
        )
        if payload.get("type") != expected_type:
            raise TokenValidationError("Unexpected token type")
        return TokenPayload(
            subject=UUID(payload["sub"]),
            session_id=UUID(payload["sid"]),
            token_type=payload["type"],
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError("Invalid or expired token") from exc


def create_scoped_token(
    subject: UUID,
    token_type: str,
    *,
    expires_at: datetime | None = None,
    claims: dict[str, Any] | None = None,
    deterministic: bool = False,
) -> str:
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        **(claims or {}),
    }
    if expires_at is not None:
        payload["exp"] = expires_at
    if not deterministic:
        payload["iat"] = datetime.now(UTC)
        payload["jti"] = str(uuid4())
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_scoped_token(
    token: str, expected_type: str, *, require_expiry: bool = False
) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp"]} if require_expiry else None,
        )
        if payload.get("type") != expected_type:
            raise TokenValidationError("Unexpected token type")
        UUID(payload["sub"])
        return payload
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError("Invalid or expired token") from exc
