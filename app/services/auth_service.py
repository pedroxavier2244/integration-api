import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ExternalServiceException, UnauthorizedException
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    create_email_token,
    decode_email_token,
)
from app.repositories.user_repository import UserRepository
from app.api.v1.schemas.auth import (
    LoginResponse,
    RefreshResponse,
    MeResponse,
    TokenPayload,
    UserTokenInfo,
)
from app.api.v1.schemas.audit import AuditAction


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_active_user_or_raise(self, repo: UserRepository, user_id: str):
        user = await repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedException(
                code="AUTH_INVALID_TOKEN",
                message="Token invalido para esta operacao.",
            )
        return user

    async def login(
        self, email: str, password: str, ip: str, user_agent: str
    ) -> LoginResponse:
        from app.services.audit_service import AuditService

        repo = UserRepository(self.db)
        user = await repo.get_by_email(email)

        if user is None or not user.is_active:
            await AuditService(self.db).log(
                action=AuditAction.login_failed,
                user_email=email,
                ip_address=ip,
                user_agent=user_agent,
                independent_transaction=True,
            )
            raise UnauthorizedException(
                code="AUTH_INVALID_CREDENTIALS",
                message="Email ou senha invalidos.",
            )

        if not user.hashed_password or not verify_password(password, user.hashed_password):
            await AuditService(self.db).log(
                action=AuditAction.login_failed,
                user_email=email,
                ip_address=ip,
                user_agent=user_agent,
                independent_transaction=True,
            )
            raise UnauthorizedException(
                code="AUTH_INVALID_CREDENTIALS",
                message="Email ou senha invalidos.",
            )

        await repo.update_last_login(user.id)

        access = create_access_token(user.id, user.email, user.role)
        refresh = create_refresh_token(user.id)

        token_hash = hashlib.sha256(refresh.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        await repo.save_refresh_token(user.id, token_hash, expires_at)

        await AuditService(self.db).log(
            action=AuditAction.login,
            user_id=user.id,
            user_email=user.email,
            ip_address=ip,
            user_agent=user_agent,
        )

        return LoginResponse(
            access_token=access,
            refresh_token=refresh,
            user=UserTokenInfo(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
            ),
        )

    async def refresh(self, refresh_token: str) -> RefreshResponse:
        user_id = decode_refresh_token(refresh_token)

        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        repo = UserRepository(self.db)
        rt = await repo.get_refresh_token(token_hash)

        now = datetime.now(timezone.utc)
        if rt is None or rt.is_revoked or rt.expires_at.replace(tzinfo=timezone.utc) < now:
            raise UnauthorizedException(
                code="AUTH_INVALID_TOKEN",
                message="Refresh token invalido ou expirado.",
            )

        user = await repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedException(
                code="AUTH_INVALID_CREDENTIALS",
                message="Usuario inativo.",
            )

        access = create_access_token(user.id, user.email, user.role)
        return RefreshResponse(access_token=access)

    async def logout(self, refresh_token: str, user_id: str) -> None:
        from app.services.audit_service import AuditService

        token_user_id = decode_refresh_token(refresh_token)
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        repo = UserRepository(self.db)
        rt = await repo.get_refresh_token(token_hash)
        now = datetime.now(timezone.utc)

        if (
            rt is None
            or rt.user_id != user_id
            or token_user_id != user_id
            or rt.is_revoked
            or rt.expires_at.replace(tzinfo=timezone.utc) < now
        ):
            raise UnauthorizedException(
                code="AUTH_INVALID_TOKEN",
                message="Refresh token invalido ou expirado.",
            )

        await repo.revoke_refresh_token(token_hash)
        await AuditService(self.db).log(
            action=AuditAction.logout,
            user_id=user_id,
        )

    async def forgot_password(self, email: str) -> None:
        from app.services.audit_service import AuditService
        from app.integrations.email_client import send_reset_password_email

        repo = UserRepository(self.db)
        user = await repo.get_by_email(email)
        if user is None or not user.is_active:
            return  # silencioso - nao vazar existencia do email

        token = create_email_token(user.id, "reset")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_RESET_TOKEN_EXPIRE_HOURS)
        await repo.save_reset_token(user.id, token_hash, expires_at)

        try:
            await send_reset_password_email(user.email, user.full_name, token)
        except Exception as exc:
            raise ExternalServiceException(
                code="EMAIL_DELIVERY_FAILED",
                message="Nao foi possivel enviar o email de redefinicao. Tente novamente mais tarde.",
            ) from exc

        await AuditService(self.db).log(
            action=AuditAction.password_reset_requested,
            user_id=user.id,
            user_email=user.email,
        )

    async def reset_password(self, token: str, new_password: str) -> None:
        from app.services.audit_service import AuditService
        from app.core.security import hash_password

        user_id = decode_email_token(token, "reset")

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        repo = UserRepository(self.db)
        rt = await repo.get_reset_token(token_hash)

        now = datetime.now(timezone.utc)
        if rt is None or rt.used or rt.expires_at.replace(tzinfo=timezone.utc) < now:
            raise UnauthorizedException(
                code="AUTH_TOKEN_EXPIRED",
                message="Token expirado ou ja utilizado.",
            )

        user = await self._get_active_user_or_raise(repo, user_id)
        await repo.set_password(user_id, hash_password(new_password))
        await repo.consume_reset_token(token_hash)
        await repo.revoke_all_user_tokens(user_id)

        await AuditService(self.db).log(
            action=AuditAction.password_reset,
            user_id=user_id,
            user_email=user.email,
        )

    async def accept_invite(self, token: str, new_password: str) -> None:
        from app.services.audit_service import AuditService
        from app.core.security import hash_password

        user_id = decode_email_token(token, "invite")

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        repo = UserRepository(self.db)
        rt = await repo.get_reset_token(token_hash)

        now = datetime.now(timezone.utc)
        if rt is None or rt.used or rt.expires_at.replace(tzinfo=timezone.utc) < now:
            raise UnauthorizedException(
                code="AUTH_TOKEN_EXPIRED",
                message="Convite expirado ou ja utilizado. Solicite um novo convite.",
            )

        user = await self._get_active_user_or_raise(repo, user_id)
        await repo.set_password(user_id, hash_password(new_password))
        await repo.consume_reset_token(token_hash)

        await AuditService(self.db).log(
            action=AuditAction.invite_accepted,
            user_id=user_id,
            user_email=user.email,
        )

    async def validate_token(self, token: str, expected_type: str) -> dict:
        try:
            user_id = decode_email_token(token, expected_type)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            repo = UserRepository(self.db)
            reset_token = await repo.get_reset_token(token_hash)
            now = datetime.now(timezone.utc)

            if (
                reset_token is None
                or reset_token.used
                or reset_token.expires_at.replace(tzinfo=timezone.utc) < now
            ):
                return {"valid": False, "email": None, "type": None}

            user = await repo.get_by_id(user_id)
            if not user or not user.is_active:
                return {"valid": False, "email": None, "type": None}

            return {"valid": True, "email": user.email, "type": expected_type}
        except Exception:
            return {"valid": False, "email": None, "type": None}

    async def get_me(self, payload: TokenPayload) -> MeResponse:
        user = await UserRepository(self.db).get_by_id(payload.sub)
        if not user or not user.is_active:
            raise UnauthorizedException(
                code="AUTH_INVALID_CREDENTIALS",
                message="Usuario nao encontrado ou inativo.",
            )
        return MeResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            permissions=payload.permissions,
            last_login_at=user.last_login_at,
        )
