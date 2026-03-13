import structlog
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.api.v1.schemas.common import HealthResponse

router = APIRouter()
logger = structlog.get_logger()


async def _check_database() -> str:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        logger.warning("health_db_check_failed", error=str(exc))
        return "unavailable"


async def _check_redis() -> str:
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        return "ok"
    except Exception as exc:
        logger.warning("health_redis_check_failed", error=str(exc))
        return "unavailable"


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    db_status = await _check_database()
    redis_status = await _check_redis()
    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        redis=redis_status,
    )
