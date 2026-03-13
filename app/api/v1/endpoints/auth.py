from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    LogoutResponse,
    MeResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    ValidateTokenRequest,
    ValidateTokenResponse,
)
from app.db.session import get_db
from app.services.auth_service import AuthService

router = APIRouter()


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=LoginResponse, summary="Autenticar usuário")
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).login(
        email=body.email,
        password=body.password,
        ip=_get_client_ip(request),
        user_agent=request.headers.get("User-Agent", ""),
    )


@router.post("/refresh", response_model=RefreshResponse, summary="Renovar access token")
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).refresh(body.refresh_token)


@router.post("/logout", response_model=LogoutResponse, summary="Encerrar sessão")
async def logout(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await AuthService(db).logout(body.refresh_token, current_user.sub)
    return LogoutResponse()


@router.get("/me", response_model=MeResponse, summary="Dados do usuário autenticado")
async def me(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await AuthService(db).get_me(current_user)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Solicitar reset de senha",
)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await AuthService(db).forgot_password(body.email)
    return ForgotPasswordResponse()


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Redefinir senha com token",
)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await AuthService(db).reset_password(body.token, body.new_password)
    return ResetPasswordResponse()


@router.post(
    "/accept-invite",
    response_model=ResetPasswordResponse,
    summary="Aceitar convite e definir senha",
)
async def accept_invite(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await AuthService(db).accept_invite(body.token, body.new_password)
    return ResetPasswordResponse(message="Senha definida com sucesso. Faça login para continuar.")


@router.post(
    "/validate-token",
    response_model=ValidateTokenResponse,
    summary="Validar token de convite ou reset",
)
async def validate_token(
    body: ValidateTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    token_type = request.query_params.get("type", "reset")
    result = await AuthService(db).validate_token(body.token, token_type)
    return ValidateTokenResponse(**result)
