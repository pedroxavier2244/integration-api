from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Any


class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: Any = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class ValidationException(AppException):
    def __init__(self, message: str, details: Any = None):
        super().__init__("VALIDATION_ERROR", message, 422, details)


class NotFoundException(AppException):
    def __init__(self, message: str = "Recurso não encontrado."):
        super().__init__("NOT_FOUND", message, 404)


class UnauthorizedException(AppException):
    def __init__(self, code: str = "AUTH_INVALID_TOKEN", message: str = "Não autorizado."):
        super().__init__(code, message, 401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Acesso negado."):
        super().__init__("AUTH_FORBIDDEN", message, 403)


class ConflictException(AppException):
    def __init__(self, code: str = "CONFLICT", message: str = "Conflito de dados."):
        super().__init__(code, message, 409)


class ExternalServiceException(AppException):
    def __init__(self, code: str = "EXTERNAL_SERVICE_ERROR", message: str = "Erro no serviço externo."):
        super().__init__(code, message, 502)


class DatabaseException(AppException):
    def __init__(self, code: str = "DATABASE_ERROR", message: str = "Erro no banco de dados."):
        super().__init__(code, message, 500)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "trace_id": trace_id,
            },
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", None)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Erro interno. Tente novamente mais tarde.",
                "details": None,
                "trace_id": trace_id,
            },
        },
    )
