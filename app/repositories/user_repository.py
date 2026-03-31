from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        full_name: str,
        role: str,
        gestor_id: Optional[str] = None,
        hashed_password: Optional[str] = None,
        must_change_password: bool = False,
    ) -> User:
        user = User(
            email=email,
            full_name=full_name,
            role=role,
            gestor_id=gestor_id,
            hashed_password=hashed_password,
            must_change_password=must_change_password,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update(self, user_id: str, **fields) -> Optional[User]:
        fields["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(update(User).where(User.id == user_id).values(**fields))
        return await self.get_by_id(user_id)

    async def deactivate(self, user_id: str) -> Optional[User]:
        return await self.update(user_id, is_active=False)

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
        role: Optional[str] = None,
        gestor_id: Optional[str] = None,
    ) -> Tuple[List[User], int]:
        query = select(User)
        count_query = select(func.count()).select_from(User)

        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        if role is not None:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)

        if gestor_id is not None:
            query = query.where(User.gestor_id == gestor_id)
            count_query = count_query.where(User.gestor_id == gestor_id)

        query = query.order_by(User.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        users = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        return users, total

    async def set_password(self, user_id: str, hashed_password: str) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                hashed_password=hashed_password,
                updated_at=datetime.now(timezone.utc),
            )
        )

    async def set_password_and_clear_must_change(self, user_id: str, hashed_password: str) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                hashed_password=hashed_password,
                must_change_password=False,
                updated_at=datetime.now(timezone.utc),
            )
        )

    async def update_last_login(self, user_id: str) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )

    async def save_refresh_token(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        rt = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(rt)
        await self.db.flush()
        return rt

    async def get_refresh_token(self, token_hash: str) -> Optional[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token_hash: str) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(is_revoked=True)
        )

    async def revoke_all_user_tokens(self, user_id: str) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,  # noqa: E712
            )
            .values(is_revoked=True)
        )

    async def save_reset_token(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        rt = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(rt)
        await self.db.flush()
        return rt

    async def get_reset_token(self, token_hash: str) -> Optional[PasswordResetToken]:
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def consume_reset_token(self, token_hash: str) -> None:
        await self.db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
            .values(used=True)
        )
