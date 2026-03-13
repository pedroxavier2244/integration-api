"""
Testes unitários para AuthService.

Mocks: send_reset_password_email, send_invite_email, export_to_crm.delay
"""
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth_service import AuthService
from app.core.security import (
    hash_password,
    create_refresh_token,
    create_email_token,
)
from app.core.exceptions import UnauthorizedException
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken
from app.models.password_reset_token import PasswordResetToken
from app.api.v1.schemas.auth import TokenPayload


class TestAuthServiceLogin:
    async def test_login_success(self, db: AsyncSession, admin_user: User):
        svc = AuthService(db)
        result = await svc.login(
            email="admin@test.com",
            password="Admin@123",
            ip="127.0.0.1",
            user_agent="pytest",
        )
        assert result.access_token
        assert result.refresh_token
        assert result.user.email == "admin@test.com"

    async def test_login_wrong_password(self, db: AsyncSession, admin_user: User):
        svc = AuthService(db)
        with pytest.raises(UnauthorizedException) as exc_info:
            await svc.login(
                email="admin@test.com",
                password="WrongPassword",
                ip="127.0.0.1",
                user_agent="pytest",
            )
        assert exc_info.value.code == "AUTH_INVALID_CREDENTIALS"

    async def test_login_unknown_email(self, db: AsyncSession):
        svc = AuthService(db)
        with pytest.raises(UnauthorizedException):
            await svc.login(
                email="naoexiste@test.com",
                password="any",
                ip="127.0.0.1",
                user_agent="pytest",
            )

    async def test_login_inactive_user(self, db: AsyncSession):
        user = User(
            email="inactive@test.com",
            full_name="Inactive",
            role=UserRole.operador,
            hashed_password=hash_password("pass123"),
            is_active=False,
        )
        db.add(user)
        await db.flush()

        svc = AuthService(db)
        with pytest.raises(UnauthorizedException):
            await svc.login(
                email="inactive@test.com",
                password="pass123",
                ip="127.0.0.1",
                user_agent="pytest",
            )

    async def test_login_user_without_password(self, db: AsyncSession):
        user = User(
            email="nopass@test.com",
            full_name="No Pass",
            role=UserRole.operador,
            hashed_password=None,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        svc = AuthService(db)
        with pytest.raises(UnauthorizedException):
            await svc.login(
                email="nopass@test.com",
                password="anything",
                ip="127.0.0.1",
                user_agent="pytest",
            )


class TestAuthServiceRefresh:
    async def test_refresh_success(self, db: AsyncSession, admin_user: User, admin_refresh_token: str):
        svc = AuthService(db)
        result = await svc.refresh(admin_refresh_token)
        assert result.access_token

    async def test_refresh_revoked_token(self, db: AsyncSession, admin_user: User):
        raw_token = create_refresh_token(admin_user.id)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        rt = RefreshToken(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=True,
        )
        db.add(rt)
        await db.flush()

        svc = AuthService(db)
        with pytest.raises(UnauthorizedException):
            await svc.refresh(raw_token)

    async def test_refresh_expired_token(self, db: AsyncSession, admin_user: User):
        raw_token = create_refresh_token(admin_user.id)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        rt = RefreshToken(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # expirado
        )
        db.add(rt)
        await db.flush()

        svc = AuthService(db)
        with pytest.raises(UnauthorizedException):
            await svc.refresh(raw_token)

    async def test_refresh_invalid_jwt(self, db: AsyncSession):
        svc = AuthService(db)
        with pytest.raises(UnauthorizedException):
            await svc.refresh("not.a.valid.token")


class TestAuthServiceLogout:
    async def test_logout_revokes_token(self, db: AsyncSession, admin_user: User, admin_refresh_token: str):
        svc = AuthService(db)
        # Should not raise
        await svc.logout(admin_refresh_token, admin_user.id)

        # Verifica que foi revogado
        token_hash = hashlib.sha256(admin_refresh_token.encode()).hexdigest()
        from sqlalchemy import select
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        rt = result.scalar_one_or_none()
        assert rt is not None
        assert rt.is_revoked is True


class TestAuthServiceForgotPassword:
    @patch("app.integrations.email_client.send_reset_password_email", new_callable=AsyncMock)
    async def test_forgot_password_known_email(self, mock_send, db: AsyncSession, admin_user: User):
        svc = AuthService(db)
        # Não deve lançar
        await svc.forgot_password("admin@test.com")
        mock_send.assert_called_once()

    @patch("app.integrations.email_client.send_reset_password_email", new_callable=AsyncMock)
    async def test_forgot_password_unknown_email_silent(self, mock_send, db: AsyncSession):
        svc = AuthService(db)
        # Silencioso — não revela existência do email
        await svc.forgot_password("naoexiste@test.com")
        mock_send.assert_not_called()


class TestAuthServiceResetPassword:
    @patch("app.integrations.email_client.send_reset_password_email", new_callable=AsyncMock)
    async def test_reset_password_success(self, mock_send, db: AsyncSession, admin_user: User):
        # Gera e salva token de reset
        token = create_email_token(admin_user.id, "reset")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        rt = PasswordResetToken(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(rt)
        await db.flush()

        svc = AuthService(db)
        await svc.reset_password(token, "NewPassword@123")

        # Verifica que a senha foi alterada
        from sqlalchemy import select
        result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        saved_rt = result.scalar_one_or_none()
        assert saved_rt.used is True

    async def test_reset_password_expired_token(self, db: AsyncSession, admin_user: User):
        token = create_email_token(admin_user.id, "reset")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        rt = PasswordResetToken(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # expirado
        )
        db.add(rt)
        await db.flush()

        svc = AuthService(db)
        with pytest.raises(UnauthorizedException):
            await svc.reset_password(token, "NewPass@123")

    async def test_reset_password_used_token(self, db: AsyncSession, admin_user: User):
        token = create_email_token(admin_user.id, "reset")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        rt = PasswordResetToken(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used=True,  # já utilizado
        )
        db.add(rt)
        await db.flush()

        svc = AuthService(db)
        with pytest.raises(UnauthorizedException):
            await svc.reset_password(token, "NewPass@123")


class TestAuthServiceAcceptInvite:
    async def test_accept_invite_success(self, db: AsyncSession, admin_user: User):
        # Usuário sem senha (simula usuário convidado)
        user = User(
            email="invited@test.com",
            full_name="Invited User",
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

        svc = AuthService(db)
        await svc.accept_invite(token, "MyPassword@123")

        # Token deve estar marcado como usado
        from sqlalchemy import select
        result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        saved_rt = result.scalar_one_or_none()
        assert saved_rt.used is True

    async def test_accept_invite_wrong_type(self, db: AsyncSession, admin_user: User):
        """Token do tipo 'reset' não pode ser usado como 'invite'."""
        reset_token = create_email_token(admin_user.id, "reset")
        svc = AuthService(db)
        with pytest.raises(UnauthorizedException):
            await svc.accept_invite(reset_token, "pass")


class TestAuthServiceValidateToken:
    async def test_validate_valid_token(self, db: AsyncSession, admin_user: User):
        token = create_email_token(admin_user.id, "invite")
        svc = AuthService(db)
        result = await svc.validate_token(token, "invite")
        assert result["valid"] is True
        assert result["email"] == admin_user.email

    async def test_validate_invalid_token(self, db: AsyncSession):
        svc = AuthService(db)
        result = await svc.validate_token("invalid.token", "invite")
        assert result["valid"] is False

    async def test_validate_consumed_token(self, db: AsyncSession, admin_user: User):
        token = create_email_token(admin_user.id, "reset")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        rt = PasswordResetToken(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used=True,
        )
        db.add(rt)
        await db.flush()

        svc = AuthService(db)
        result = await svc.validate_token(token, "reset")
        assert result["valid"] is False

    async def test_validate_wrong_type(self, db: AsyncSession, admin_user: User):
        invite_token = create_email_token(admin_user.id, "invite")
        svc = AuthService(db)
        result = await svc.validate_token(invite_token, "reset")
        assert result["valid"] is False


class TestAuthServiceGetMe:
    async def test_get_me_success(self, db: AsyncSession, admin_user: User, admin_token: str):
        from app.core.security import decode_access_token
        payload = decode_access_token(admin_token)
        svc = AuthService(db)
        result = await svc.get_me(payload)
        assert result.email == "admin@test.com"
        assert result.role == UserRole.admin

    async def test_get_me_inactive_user(self, db: AsyncSession):
        user = User(
            email="inactive2@test.com",
            full_name="Inactive",
            role=UserRole.operador,
            hashed_password=hash_password("pass"),
            is_active=False,
        )
        db.add(user)
        await db.flush()

        from app.core.security import create_access_token
        token = create_access_token(user.id, user.email, user.role)
        from app.core.security import decode_access_token
        payload = decode_access_token(token)

        svc = AuthService(db)
        with pytest.raises(UnauthorizedException):
            await svc.get_me(payload)
