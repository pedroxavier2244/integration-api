from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.audit import AuditAction
from app.api.v1.schemas.users import (
    CreateUserResponse,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
    UserRole,
)
from app.core.config import settings
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.security import create_email_token, hash_password
from app.repositories.user_repository import UserRepository

TEMP_PASSWORD = "Trocar@123"


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_actor_or_raise(self, repo: UserRepository, actor_id: str):
        actor = await repo.get_by_id(actor_id)
        if not actor or not actor.is_active:
            raise ForbiddenException(message="Usuario autenticado nao esta ativo.")
        return actor

    async def _get_target_or_raise(self, repo: UserRepository, user_id: str):
        user = await repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(message="Usuario nao encontrado.")
        return user

    async def _validate_gestor_reference(
        self,
        repo: UserRepository,
        gestor_id: Optional[str],
    ) -> Optional[str]:
        if gestor_id is None:
            return None

        gestor = await repo.get_by_id(gestor_id)
        if not gestor or not gestor.is_active or UserRole(gestor.role) != UserRole.gestor:
            raise ValidationException(message="Gestor informado nao existe ou esta inativo.")
        return gestor.id

    def _can_read_user(self, actor: Any, target: Any) -> bool:
        actor_role = UserRole(actor.role)
        if actor_role == UserRole.admin:
            return True
        if actor_role == UserRole.gestor:
            return target.id == actor.id or (
                UserRole(target.role) == UserRole.operador and target.gestor_id == actor.id
            )
        return False

    def _ensure_gestor_team_scope(
        self,
        actor: Any,
        target: Any,
        updates: dict[str, Any],
    ) -> None:
        if UserRole(target.role) != UserRole.operador:
            raise ForbiddenException(
                message="Gestor so pode gerenciar operadores da propria equipe."
            )

        if "role" in updates and updates["role"] is not None and updates["role"] != UserRole.operador:
            raise ForbiddenException(
                message="Gestor nao pode promover operador para gestor ou admin."
            )

        requested_gestor_supplied = "gestor_id" in updates
        requested_gestor_id = updates.get("gestor_id")

        if target.gestor_id == actor.id:
            if requested_gestor_supplied and requested_gestor_id not in (None, actor.id):
                raise ForbiddenException(
                    message="Gestor so pode adicionar ou remover operador da propria equipe."
                )
            return

        if target.gestor_id is None and requested_gestor_supplied and requested_gestor_id == actor.id:
            return

        raise ForbiddenException(
            message="Gestor so pode gerenciar operadores da propria equipe."
        )

    async def _build_create_gestor_id(
        self,
        repo: UserRepository,
        actor: Any,
        role: UserRole,
        requested_gestor_id: Optional[str],
    ) -> Optional[str]:
        actor_role = UserRole(actor.role)

        if actor_role == UserRole.gestor:
            if role != UserRole.operador:
                raise ForbiddenException(
                    message="Gestor so pode criar usuarios com role operador."
                )
            if requested_gestor_id is not None and requested_gestor_id != actor.id:
                raise ForbiddenException(
                    message="Gestor so pode criar operadores na propria equipe."
                )
            return actor.id

        if role != UserRole.operador:
            if requested_gestor_id is not None:
                raise ValidationException(
                    message="Somente operadores podem ser vinculados a um gestor."
                )
            return None

        return await self._validate_gestor_reference(repo, requested_gestor_id)

    async def _build_update_fields(
        self,
        repo: UserRepository,
        actor: Any,
        target: Any,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        actor_role = UserRole(actor.role)
        current_role = UserRole(target.role)
        final_role = (
            updates["role"] if "role" in updates and updates["role"] is not None else current_role
        )
        fields: dict[str, Any] = {}

        if "full_name" in updates and updates["full_name"] is not None:
            full_name = updates["full_name"].strip()
            if not full_name:
                raise ValidationException(message="Nome completo nao pode ser vazio.")
            fields["full_name"] = full_name

        if actor_role == UserRole.gestor:
            self._ensure_gestor_team_scope(actor, target, updates)
            if "role" in updates:
                fields["role"] = UserRole.operador.value
            if "gestor_id" in updates:
                fields["gestor_id"] = actor.id if updates["gestor_id"] == actor.id else None
            return fields

        if "role" in updates and updates["role"] is not None:
            fields["role"] = final_role.value

        if final_role != UserRole.operador:
            if "gestor_id" in updates and updates["gestor_id"] is not None:
                raise ValidationException(
                    message="Somente operadores podem ser vinculados a um gestor."
                )
            fields["gestor_id"] = None
            return fields

        if "gestor_id" in updates:
            fields["gestor_id"] = await self._validate_gestor_reference(
                repo,
                updates["gestor_id"],
            )
        elif current_role != UserRole.operador:
            fields["gestor_id"] = None

        return fields

    async def create_user(
        self,
        email: str,
        full_name: str,
        role: UserRole,
        created_by_id: str,
        gestor_id: Optional[str] = None,
    ) -> CreateUserResponse:
        from app.services.audit_service import AuditService

        repo = UserRepository(self.db)
        actor = await self._get_actor_or_raise(repo, created_by_id)
        existing = await repo.get_by_email(email)
        if existing:
            raise ConflictException(
                code="USER_EMAIL_EXISTS",
                message="Email ja cadastrado.",
            )

        final_gestor_id = await self._build_create_gestor_id(
            repo=repo,
            actor=actor,
            role=role,
            requested_gestor_id=gestor_id,
        )

        user = await repo.create(
            email=email,
            full_name=full_name.strip(),
            role=role.value,
            gestor_id=final_gestor_id,
            hashed_password=hash_password(TEMP_PASSWORD),
            must_change_password=True,
        )

        await AuditService(self.db).log(
            action=AuditAction.user_created,
            user_id=created_by_id,
            resource="user",
            resource_id=user.id,
            payload={"role": role.value, "gestor_id": final_gestor_id},
        )

        return CreateUserResponse.model_validate(user)

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
        actor_id: Optional[str] = None,
    ) -> UserListResponse:
        repo = UserRepository(self.db)
        actor = await self._get_actor_or_raise(repo, actor_id) if actor_id else None

        filters: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "is_active": is_active,
        }

        if actor and UserRole(actor.role) == UserRole.gestor:
            filters["role"] = UserRole.operador.value
            filters["gestor_id"] = actor.id

        users, total = await repo.list_users(**filters)
        return UserListResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_user(self, user_id: str, actor_id: str) -> UserResponse:
        repo = UserRepository(self.db)
        actor = await self._get_actor_or_raise(repo, actor_id)
        user = await self._get_target_or_raise(repo, user_id)

        if not self._can_read_user(actor, user):
            raise ForbiddenException(
                message="Voce nao pode visualizar usuarios fora do seu escopo."
            )

        return UserResponse.model_validate(user)

    async def update_user(
        self,
        user_id: str,
        updates: dict[str, Any],
        updated_by_id: str,
    ) -> UserResponse:
        from app.services.audit_service import AuditService

        repo = UserRepository(self.db)
        actor = await self._get_actor_or_raise(repo, updated_by_id)
        user = await self._get_target_or_raise(repo, user_id)

        fields = await self._build_update_fields(repo, actor, user, updates)
        if fields:
            user = await repo.update(user_id, **fields)

        await AuditService(self.db).log(
            action=AuditAction.user_updated,
            user_id=updated_by_id,
            resource="user",
            resource_id=user_id,
            payload=fields or None,
        )

        return UserResponse.model_validate(user)

    async def deactivate_user(self, user_id: str, deactivated_by_id: str) -> None:
        from app.services.audit_service import AuditService

        if user_id == deactivated_by_id:
            raise ForbiddenException(
                message="Voce nao pode desativar sua propria conta.",
            )

        repo = UserRepository(self.db)
        actor = await self._get_actor_or_raise(repo, deactivated_by_id)
        user = await self._get_target_or_raise(repo, user_id)

        if UserRole(actor.role) == UserRole.gestor and (
            UserRole(user.role) != UserRole.operador or user.gestor_id != actor.id
        ):
            raise ForbiddenException(
                message="Gestor so pode desativar operadores da propria equipe."
            )

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
        actor = await self._get_actor_or_raise(repo, revoked_by_id)
        user = await self._get_target_or_raise(repo, user_id)

        if UserRole(actor.role) == UserRole.gestor and (
            UserRole(user.role) != UserRole.operador or user.gestor_id != actor.id
        ):
            raise ForbiddenException(
                message="Gestor so pode revogar sessoes de operadores da propria equipe."
            )

        await repo.revoke_all_user_tokens(user_id)

        await AuditService(self.db).log(
            action=AuditAction.sessions_revoked,
            user_id=revoked_by_id,
            resource="user",
            resource_id=user_id,
        )

    async def resend_invite(self, user_id: str, resent_by_id: str) -> None:
        from app.integrations.email_client import send_invite_email
        from app.services.audit_service import AuditService

        repo = UserRepository(self.db)
        actor = await self._get_actor_or_raise(repo, resent_by_id)
        user = await self._get_target_or_raise(repo, user_id)

        if UserRole(actor.role) == UserRole.gestor and (
            UserRole(user.role) != UserRole.operador or user.gestor_id != actor.id
        ):
            raise ForbiddenException(
                message="Gestor so pode reenviar convite para operadores da propria equipe."
            )

        if not user.is_active:
            raise ForbiddenException(message="Usuario inativo.")
        if user.hashed_password is not None:
            raise ConflictException(message="Usuario ja definiu sua senha.")

        token = create_email_token(user.id, "invite")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.JWT_INVITE_TOKEN_EXPIRE_HOURS
        )
        await repo.save_reset_token(user.id, token_hash, expires_at)

        await send_invite_email(user.email, user.full_name, token)

        await AuditService(self.db).log(
            action=AuditAction.invite_sent,
            user_id=resent_by_id,
            resource="user",
            resource_id=user_id,
        )
