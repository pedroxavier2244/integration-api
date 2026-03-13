"""
Testes de integração para os endpoints de autenticação.

POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
POST /api/v1/auth/accept-invite
POST /api/v1/auth/validate-token
"""
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.password_reset_token import PasswordResetToken
from app.core.security import hash_password, create_email_token


BASE = "/api/v1/auth"

# Senha forte que passa no validador (8+ chars, 1 maiúscula, 1 número)
STRONG_PASSWORD = "NewPassword@123"


class TestLoginEndpoint:
    async def test_login_success(self, client: AsyncClient, admin_user: User):
        resp = await client.post(f"{BASE}/login", json={
            "email": "admin@test.com",
            "password": "Admin@123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "admin@test.com"

    async def test_login_wrong_password(self, client: AsyncClient, admin_user: User):
        resp = await client.post(f"{BASE}/login", json={
            "email": "admin@test.com",
            "password": "WrongPass",
        })
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/login", json={
            "email": "naoexiste@test.com",
            "password": "any",
        })
        assert resp.status_code == 401

    async def test_login_missing_fields(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/login", json={"email": "admin@test.com"})
        assert resp.status_code == 422

    async def test_login_invalid_email_format(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/login", json={
            "email": "not-an-email",
            "password": "pass",
        })
        assert resp.status_code == 422


class TestRefreshEndpoint:
    async def test_refresh_success(self, client: AsyncClient, admin_user: User, admin_refresh_token: str):
        resp = await client.post(f"{BASE}/refresh", json={
            "refresh_token": admin_refresh_token,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    async def test_refresh_invalid_token(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/refresh", json={
            "refresh_token": "invalid.token.here",
        })
        assert resp.status_code == 401

    async def test_refresh_missing_token(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/refresh", json={})
        assert resp.status_code == 422


class TestLogoutEndpoint:
    async def test_logout_success(self, client: AsyncClient, admin_user: User, admin_token: str, admin_refresh_token: str):
        resp = await client.post(
            f"{BASE}/logout",
            json={"refresh_token": admin_refresh_token},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_logout_without_auth(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/logout", json={"refresh_token": "any"})
        assert resp.status_code == 403

    async def test_logout_missing_refresh_token(self, client: AsyncClient, admin_token: str):
        resp = await client.post(
            f"{BASE}/logout",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422


class TestMeEndpoint:
    async def test_get_me_success(self, client: AsyncClient, admin_user: User, admin_token: str):
        resp = await client.get(
            f"{BASE}/me",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"
        assert "permissions" in data

    async def test_get_me_without_token(self, client: AsyncClient):
        resp = await client.get(f"{BASE}/me")
        assert resp.status_code == 403

    async def test_get_me_invalid_token(self, client: AsyncClient):
        resp = await client.get(
            f"{BASE}/me",
            headers={"Authorization": "Bearer invalid.token"},
        )
        assert resp.status_code == 401


class TestForgotPasswordEndpoint:
    @patch("app.integrations.email_client.send_reset_password_email", new_callable=AsyncMock)
    async def test_forgot_password_known_email(self, mock_send, client: AsyncClient, admin_user: User):
        resp = await client.post(f"{BASE}/forgot-password", json={
            "email": "admin@test.com",
        })
        # Retorna 200 com resposta silenciosa
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_send.assert_called_once()

    @patch("app.integrations.email_client.send_reset_password_email", new_callable=AsyncMock)
    async def test_forgot_password_unknown_email(self, mock_send, client: AsyncClient):
        resp = await client.post(f"{BASE}/forgot-password", json={
            "email": "naoexiste@test.com",
        })
        # Silencioso — sempre retorna 200 para não vazar existência do email
        assert resp.status_code == 200
        mock_send.assert_not_called()

    async def test_forgot_password_invalid_email(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/forgot-password", json={
            "email": "not-an-email",
        })
        assert resp.status_code == 422


class TestResetPasswordEndpoint:
    async def test_reset_password_success(self, client: AsyncClient, db: AsyncSession, admin_user: User):
        token = create_email_token(admin_user.id, "reset")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        rt = PasswordResetToken(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(rt)
        await db.flush()

        resp = await client.post(f"{BASE}/reset-password", json={
            "token": token,
            "new_password": STRONG_PASSWORD,
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_reset_password_expired_token(self, client: AsyncClient, db: AsyncSession, admin_user: User):
        token = create_email_token(admin_user.id, "reset")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        rt = PasswordResetToken(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.add(rt)
        await db.flush()

        resp = await client.post(f"{BASE}/reset-password", json={
            "token": token,
            "new_password": STRONG_PASSWORD,
        })
        assert resp.status_code == 401

    async def test_reset_password_invalid_token(self, client: AsyncClient):
        """Token JWT inválido deve retornar 401."""
        resp = await client.post(f"{BASE}/reset-password", json={
            "token": "invalid.token.here",
            "new_password": STRONG_PASSWORD,
        })
        assert resp.status_code == 401

    async def test_reset_password_weak_password(self, client: AsyncClient, admin_user: User):
        """Senha fraca deve retornar 422 antes de verificar o token."""
        token = create_email_token(admin_user.id, "reset")
        resp = await client.post(f"{BASE}/reset-password", json={
            "token": token,
            "new_password": "weak",
        })
        assert resp.status_code == 422


class TestAcceptInviteEndpoint:
    async def test_accept_invite_success(self, client: AsyncClient, db: AsyncSession):
        user = User(
            email="invited_ep@test.com",
            full_name="Invited EP",
            role=UserRole.operador,
            hashed_password=None,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        token = create_email_token(user.id, "invite")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        rt = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        )
        db.add(rt)
        await db.flush()

        resp = await client.post(f"{BASE}/accept-invite", json={
            "token": token,
            "new_password": "MyNewPassword@789",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_accept_invite_wrong_token_type(self, client: AsyncClient, admin_user: User):
        """Token do tipo 'reset' não pode ser usado como 'invite'."""
        reset_token = create_email_token(admin_user.id, "reset")
        resp = await client.post(f"{BASE}/accept-invite", json={
            "token": reset_token,
            "new_password": STRONG_PASSWORD,  # senha válida para isolar teste do token
        })
        assert resp.status_code == 401

    async def test_accept_invite_weak_password(self, client: AsyncClient, admin_user: User):
        token = create_email_token(admin_user.id, "invite")
        resp = await client.post(f"{BASE}/accept-invite", json={
            "token": token,
            "new_password": "weak",
        })
        assert resp.status_code == 422


class TestValidateTokenEndpoint:
    async def test_validate_valid_invite_token(self, client: AsyncClient, admin_user: User):
        token = create_email_token(admin_user.id, "invite")
        # validate-token é POST com body e type como query param
        resp = await client.post(
            f"{BASE}/validate-token",
            json={"token": token},
            params={"type": "invite"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["email"] == admin_user.email

    async def test_validate_invalid_token(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE}/validate-token",
            json={"token": "invalid.token.here"},
            params={"type": "invite"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False

    async def test_validate_wrong_type(self, client: AsyncClient, admin_user: User):
        invite_token = create_email_token(admin_user.id, "invite")
        resp = await client.post(
            f"{BASE}/validate-token",
            json={"token": invite_token},
            params={"type": "reset"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
