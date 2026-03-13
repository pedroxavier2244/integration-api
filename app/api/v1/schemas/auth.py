from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional
from datetime import datetime
import re


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Senha não pode ser vazia.")
        return v


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    user: "UserTokenInfo"


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600


class TokenPayload(BaseModel):
    sub: str
    email: str
    role: str
    permissions: List[str]
    jti: str
    exp: Optional[int] = None


class LogoutResponse(BaseModel):
    success: bool = True
    message: str = "Sessão encerrada com sucesso."


class UserTokenInfo(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    permissions: List[str]
    last_login_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    success: bool = True
    message: str = "Se o email estiver cadastrado, você receberá um link em instantes."


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("A senha deve ter no mínimo 8 caracteres.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("A senha deve conter pelo menos uma letra maiúscula.")
        if not re.search(r"[0-9]", v):
            raise ValueError("A senha deve conter pelo menos um número.")
        return v


class ResetPasswordResponse(BaseModel):
    success: bool = True
    message: str = "Senha redefinida com sucesso. Faça login para continuar."


class ValidateTokenRequest(BaseModel):
    token: str


class ValidateTokenResponse(BaseModel):
    valid: bool
    email: Optional[str] = None
    type: Optional[str] = None
