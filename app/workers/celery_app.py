"""
Configuração do Celery para processamento assíncrono.

Broker: Redis (REDIS_URL no .env)
Backend: Redis (para rastreamento de status de tasks)

Para iniciar o worker na VPS:
    celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

Para monitorar:
    celery -A app.workers.celery_app flower
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "integration_api",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    # Serialização
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,

    # Retry e reliability
    task_acks_late=True,                  # confirma só após execução (não na entrega)
    task_reject_on_worker_lost=True,      # recoloca na fila se worker morrer
    worker_prefetch_multiplier=1,         # processa 1 task por vez por worker

    # Dead Letter Queue — tasks que falharam após max_retries
    task_routes={
        "app.workers.tasks.export_to_crm": {"queue": "crm_outbound"},
    },

    # Resultados expiram em 24h
    result_expires=86400,
)
