import hashlib
from typing import Optional
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, NotFoundException, ForbiddenException
from app.core.security import create_email_token
from app.repositories.user_repository import UserRepository
from app.api.v1.schemas.users import (
    CreateUserResponse,
    UserResponse,
    UserListResponse,
    UserRole,
)
from app.api.v1.schemas.audit import AuditAction


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_user(
        self,
        email: str,
        full_name: str,
        role: UserRole,
        created_by_id: str,
    ) -> CreateUserResponse:
        from app.services.audit_service import AuditService
        from app.integrations.email_client import send_invite_email

        repo = UserRepository(self.db)
        existing = await repo.get_by_email(email)
        if existing:
            raise ConflictException(
                code="USER_EMAIL_EXISTS",
                message="Email já cadastrado.",
            )

        user = await repo.create(email=email, full_name=full_name, role=role.value)

        token = create_email_token(user.id, "invite")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_INVITE_TOKEN_EXPIRE_HOURS)
        await repo.save_reset_token(user.id, token_hash, expires_at)

        await send_invite_email(user.email, user.full_name, token)

        await AuditService(self.db).log(
            action=AuditAction.user_created,
            user_id=created_by_id,
            resource="user",
            resource_id=user.id,
        )

        return CreateUserResponse.model_validate(user)

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
    ) -> UserListResponse:
        users, total = await UserRepository(self.db).list_users(page, page_size, is_active)
        return UserListResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_user(self, user_id: str) -> UserResponse:
        user = await UserRepository(self.db).get_by_id(user_id)
        if not user:
            raise NotFoundException(message="Usuário não encontrado.")
        return UserResponse.model_validate(user)

    async def update_user(
        self,
        user_id: str,
        full_name: Optional[str],
        role: Optional[UserRole],
        updated_by_id: str,
    ) -> UserResponse:
        from app.services.audit_service import AuditService

        repo = UserRepository(self.db)
        user = await repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(message="Usuário não encontrado.")

        fields = {}
        if full_name:
            fields["full_name"] = full_name
        if role:
            fields["role"] = role.value
        if fields:
            user = await repo.update(user_id, **fields)

        await AuditService(self.db).log(
            action=AuditAction.user_updated,
            user_id=updated_by_id,
            resource="user",
            resource_id=user_id,
        )

        return UserResponse.model_validate(user)

    async def deactivate_user(self, user_id: str, deactivated_by_id: str) -> None:
        from app.services.audit_service import AuditService

        if user_id == deactivated_by_id:
            raise ForbiddenException(
                message="Você não pode desativar sua própria conta.",
            )

        repo = UserRepository(self.db)
        user = await repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(message="Usuário não encontrado.")

        await repo.deactivate(user_id)
        await repo.revoke_all_user_tokens(user_id)

        await AuditService(self.db).log(
            action=AuditAction.user_deactivated,
            user_id=deactivated_by_id,
            resource="user",
            resource_id=user_id,
        )

    async def revoke_sessions(self, user_id: str, revoked_by_id: str) -> None:
        from app.services.audit_service import AuditService

        repo = UserRepository(self.db)
        user = await repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(message="Usuário não encontrado.")

        await repo.revoke_all_user_tokens(user_id)

        await AuditService(self.db).log(
            action=AuditAction.sessions_revoked,
            user_id=revoked_by_id,
            resource="user",
            resource_id=user_id,
        )

    async def resend_invite(self, user_id: str, resent_by_id: str) -> None:
        from app.services.audit_service import AuditService
        from app.integrations.email_client import send_invite_email

        repo = UserRepository(self.db)
        user = await repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(message="Usuário não encontrado.")
        if not user.is_active:
            raise ForbiddenException(message="Usuário inativo.")
        if user.hashed_password is not None:
            raise ConflictException(message="Usuário já definiu sua senha.")

        token = create_email_token(user.id, "invite")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_INVITE_TOKEN_EXPIRE_HOURS)
        await repo.save_reset_token(user.id, token_hash, expires_at)

        await send_invite_email(user.email, user.full_name, token)

        await AuditService(self.db).log(
            action=AuditAction.invite_sent,
            user_id=resent_by_id,
            resource="user",
            resource_id=user_id,
        )
