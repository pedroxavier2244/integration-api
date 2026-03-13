"""
Tasks Celery da Integration API.

export_to_crm: processa um CrmOutboundJob, lê clientes do banco
e os envia para o CRM externo em lotes.

Retry automático com backoff exponencial:
  tentativa 1 → imediato
  tentativa 2 → 60s
  tentativa 3 → 120s
  tentativa 4 → 240s
  após 4 falhas → task vai para a DLQ (Dead Letter Queue)
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from celery import Task
from celery.exceptions import MaxRetriesExceededError

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# ─── Helper para rodar código async dentro de tasks síncronas do Celery ───────

def _run(coro):
    """Executa coroutine async em contexto síncrono do Celery."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─── Task principal ────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.workers.tasks.export_to_crm",
    max_retries=4,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
)
def export_to_crm(self: Task, job_id: str) -> dict:
    """
    Processa um job de exportação de clientes para o CRM.

    1. Marca job como RUNNING
    2. Lê filtros do job
    3. Busca clientes em final_visao_cliente (paginado, lotes de 500)
    4. Envia cada lote para o CRM externo
    5. Atualiza job com sent/failed/status=DONE
    6. Em caso de falha: retry com backoff, após max_retries → status=FAILED
    """
    return _run(_export_to_crm_async(self, job_id))


async def _export_to_crm_async(task: Task, job_id: str) -> dict:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.core.config import settings
    from app.repositories.crm_repository import CrmRepository
    from app.repositories.visao_cliente_repository import VisaoClienteRepository

    _is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    engine = create_async_engine(
        settings.DATABASE_URL,
        **({} if _is_sqlite else {
            "pool_size": 5,
            "max_overflow": 10,
        })
    )
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        crm_repo = CrmRepository(db)
        job = await crm_repo.get_outbound_job(job_id)

        if not job:
            logger.error(f"export_to_crm: job {job_id} não encontrado")
            return {"error": "job_not_found"}

        # Marca como rodando
        await crm_repo.update_outbound_job(
            job_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        await db.commit()

        visao_repo = VisaoClienteRepository(db)
        filters = job.filters or {}

        sent = 0
        failed = 0
        errors = []
        page = 1
        page_size = 500

        try:
            while True:
                items, total = await visao_repo.search(
                    q=filters.get("q"),
                    page=page,
                    page_size=page_size,
                )

                if not items:
                    break

                # Atualiza total na primeira página
                if page == 1:
                    await crm_repo.update_outbound_job(job_id, total_records=total)
                    await db.commit()

                # Envia lote para CRM (implementar chamada HTTP real aqui)
                batch_sent, batch_failed, batch_errors = await _send_batch_to_crm(items, job_id)
                sent += batch_sent
                failed += batch_failed
                errors.extend(batch_errors)

                # Atualiza progresso
                await crm_repo.update_outbound_job(job_id, sent=sent, failed=failed)
                await db.commit()

                if len(items) < page_size:
                    break
                page += 1

            # Finaliza com sucesso
            final_status = "sent" if failed == 0 else "failed"
            await crm_repo.update_outbound_job(
                job_id,
                status=final_status,
                finished_at=datetime.now(timezone.utc),
                errors=errors[:100] if errors else None,  # limita erros armazenados
            )
            await db.commit()

            logger.info(f"export_to_crm {job_id}: sent={sent} failed={failed}")
            return {"job_id": job_id, "sent": sent, "failed": failed}

        except Exception as exc:
            await crm_repo.update_outbound_job(
                job_id,
                status="failed",
                finished_at=datetime.now(timezone.utc),
                errors=[{"error": str(exc)}],
            )
            await db.commit()
            raise

    await engine.dispose()


async def _send_batch_to_crm(items, job_id: str):
    """
    Envia um lote de clientes para o CRM externo via HTTP.

    TODO: implementar quando o endpoint do CRM for definido.
    Por enquanto simula sucesso para todos os registros.
    """
    # Exemplo de implementação real:
    # async with httpx.AsyncClient() as client:
    #     payload = [serialize_cliente(item) for item in items]
    #     response = await client.post(
    #         settings.CRM_WEBHOOK_URL,
    #         json=payload,
    #         headers={"Authorization": f"Bearer {settings.CRM_API_KEY}"},
    #         timeout=30,
    #     )
    #     response.raise_for_status()

    # Simulação (remover quando CRM estiver definido)
    return len(items), 0, []
