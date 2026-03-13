from pydantic import BaseModel
from typing import Any, Optional, Generic, TypeVar, List

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    trace_id: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorBody


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    redis: str
