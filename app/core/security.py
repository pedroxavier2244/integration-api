import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt
from jose import JWTError, jwt
from pydantic import ValidationError

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.api.v1.schemas.auth import TokenPayload
from app.api.v1.schemas.users import UserRole, get_permissions


def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["iat"] = datetime.now(timezone.utc)
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    payload["jti"] = str(uuid.uuid4())
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, email: str, role: UserRole) -> str:
    return _create_token(
        data={
            "sub": user_id,
            "email": email,
            "role": role,
            "permissions": get_permissions(role),
        },
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        data={"sub": user_id, "type": "refresh"},
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return TokenPayload(**payload)
    except (JWTError, ValidationError, KeyError, TypeError):
        raise UnauthorizedException(code="AUTH_INVALID_TOKEN", message="Token invalido ou expirado.")


def decode_refresh_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise UnauthorizedException(code="AUTH_INVALID_TOKEN", message="Token invalido.")
        user_id = payload["sub"]
        if not isinstance(user_id, str) or not user_id:
            raise UnauthorizedException(code="AUTH_INVALID_TOKEN", message="Token invalido.")
        return user_id
    except (JWTError, ValidationError, KeyError, TypeError):
        raise UnauthorizedException(code="AUTH_INVALID_TOKEN", message="Refresh token invalido ou expirado.")


def create_email_token(user_id: str, token_type: str) -> str:
    expire_hours = (
        settings.JWT_INVITE_TOKEN_EXPIRE_HOURS
        if token_type == "invite"
        else settings.JWT_RESET_TOKEN_EXPIRE_HOURS
    )
    return _create_token(
        data={"sub": user_id, "type": token_type},
        expires_delta=timedelta(hours=expire_hours),
    )


def decode_email_token(token: str, expected_type: str) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != expected_type:
            raise UnauthorizedException(code="AUTH_INVALID_TOKEN", message="Token invalido para esta operacao.")
        user_id = payload["sub"]
        if not isinstance(user_id, str) or not user_id:
            raise UnauthorizedException(code="AUTH_INVALID_TOKEN", message="Token invalido para esta operacao.")
        return user_id
    except (JWTError, ValidationError, KeyError, TypeError):
        raise UnauthorizedException(code="AUTH_TOKEN_EXPIRED", message="Token expirado ou invalido. Solicite um novo link.")
