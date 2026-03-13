"""
Testes unitarios para app.core.security.

Cobre: hash/verify password, create/decode access token,
create/decode refresh token, create/decode email token.
"""
import pytest
from jose import jwt

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_refresh_token,
    decode_refresh_token,
    create_email_token,
    decode_email_token,
)
from app.core.exceptions import UnauthorizedException
from app.api.v1.schemas.users import UserRole
from app.core.config import settings


class TestPasswordHashing:
    def test_hash_returns_string(self):
        result = hash_password("mypassword")
        assert isinstance(result, str)
        assert len(result) > 20

    def test_verify_correct_password(self):
        hashed = hash_password("correct")
        assert verify_password("correct", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_same_password_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False


class TestAccessToken:
    def test_create_returns_string(self):
        token = create_access_token("user-123", "user@test.com", UserRole.admin)
        assert isinstance(token, str)

    def test_decode_valid_token(self):
        token = create_access_token("user-123", "user@test.com", UserRole.admin)
        payload = decode_access_token(token)
        assert payload.sub == "user-123"
        assert payload.email == "user@test.com"
        assert payload.role == "admin"

    def test_decode_permissions_admin(self):
        token = create_access_token("u", "u@t.com", UserRole.admin)
        payload = decode_access_token(token)
        assert "users:manage" in payload.permissions
        assert "clientes:read" in payload.permissions
        assert "audit:read" in payload.permissions

    def test_decode_permissions_operador(self):
        token = create_access_token("u", "u@t.com", UserRole.operador)
        payload = decode_access_token(token)
        assert "clientes:read" in payload.permissions
        assert "users:manage" not in payload.permissions
        assert "audit:read" not in payload.permissions

    def test_decode_invalid_token_raises(self):
        with pytest.raises(UnauthorizedException):
            decode_access_token("not.a.valid.jwt")

    def test_decode_tampered_token_raises(self):
        token = create_access_token("u", "u@t.com", UserRole.admin)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(UnauthorizedException):
            decode_access_token(tampered)

    def test_token_contains_jti(self):
        token = create_access_token("u", "u@t.com", UserRole.admin)
        raw = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "jti" in raw

    def test_two_tokens_have_different_jti(self):
        t1 = create_access_token("u", "u@t.com", UserRole.admin)
        t2 = create_access_token("u", "u@t.com", UserRole.admin)
        p1 = jwt.decode(t1, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        p2 = jwt.decode(t2, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert p1["jti"] != p2["jti"]


class TestRefreshToken:
    def test_create_returns_string(self):
        token = create_refresh_token("user-123")
        assert isinstance(token, str)

    def test_decode_returns_user_id(self):
        token = create_refresh_token("user-123")
        user_id = decode_refresh_token(token)
        assert user_id == "user-123"

    def test_decode_invalid_token_raises(self):
        with pytest.raises(UnauthorizedException):
            decode_refresh_token("invalid")

    def test_access_token_not_valid_as_refresh(self):
        access = create_access_token("u", "u@t.com", UserRole.admin)
        with pytest.raises(UnauthorizedException):
            decode_refresh_token(access)

    def test_refresh_token_not_valid_as_access(self):
        refresh = create_refresh_token("user-123")
        with pytest.raises(UnauthorizedException):
            decode_access_token(refresh)


class TestEmailToken:
    def test_create_invite_token(self):
        token = create_email_token("user-123", "invite")
        user_id = decode_email_token(token, "invite")
        assert user_id == "user-123"

    def test_create_reset_token(self):
        token = create_email_token("user-456", "reset")
        user_id = decode_email_token(token, "reset")
        assert user_id == "user-456"

    def test_wrong_type_raises(self):
        invite_token = create_email_token("u", "invite")
        with pytest.raises(UnauthorizedException):
            decode_email_token(invite_token, "reset")

    def test_invalid_token_raises(self):
        with pytest.raises(UnauthorizedException):
            decode_email_token("not.valid", "invite")
