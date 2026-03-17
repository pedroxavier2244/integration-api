from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireUsersManage
from app.api.v1.schemas.users import (
    CreateUserRequest,
    CreateUserResponse,
    DeactivateUserResponse,
    ResendInviteResponse,
    RevokeSessionsResponse,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)
from app.db.session import get_db
from app.services.user_service import UserService

router = APIRouter()


@router.post("/", response_model=CreateUserResponse, status_code=201, summary="Criar usuario e enviar convite")
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user=RequireUsersManage,
):
    return await UserService(db).create_user(
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        created_by_id=current_user.sub,
        gestor_id=body.gestor_id,
    )


@router.get("/", response_model=UserListResponse, summary="Listar usuarios")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=RequireUsersManage,
):
    return await UserService(db).list_users(
        page=page,
        page_size=page_size,
        is_active=is_active,
        actor_id=current_user.sub,
    )


@router.get("/{user_id}", response_model=UserResponse, summary="Detalhe de usuario")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=RequireUsersManage,
):
    return await UserService(db).get_user(user_id, actor_id=current_user.sub)


@router.patch("/{user_id}", response_model=UserResponse, summary="Atualizar usuario")
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user=RequireUsersManage,
):
    updates = body.model_dump(exclude_unset=True)
    return await UserService(db).update_user(
        user_id=user_id,
        updates=updates,
        updated_by_id=current_user.sub,
    )


@router.delete("/{user_id}", response_model=DeactivateUserResponse, summary="Desativar usuario")
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=RequireUsersManage,
):
    await UserService(db).deactivate_user(
        user_id=user_id,
        deactivated_by_id=current_user.sub,
    )
    return DeactivateUserResponse()


@router.post(
    "/{user_id}/revoke-sessions",
    response_model=RevokeSessionsResponse,
    summary="Revogar todas as sessoes",
)
async def revoke_sessions(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=RequireUsersManage,
):
    await UserService(db).revoke_sessions(
        user_id=user_id,
        revoked_by_id=current_user.sub,
    )
    return RevokeSessionsResponse()


@router.post(
    "/{user_id}/resend-invite",
    response_model=ResendInviteResponse,
    summary="Reenviar convite",
)
async def resend_invite(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=RequireUsersManage,
):
    await UserService(db).resend_invite(
        user_id=user_id,
        resent_by_id=current_user.sub,
    )
    return ResendInviteResponse()
