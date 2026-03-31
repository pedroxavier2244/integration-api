from typing import Optional, List, Tuple
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        action: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> AuditLog:
        log = AuditLog(
            action=action,
            user_id=user_id,
            user_email=user_email,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            payload=payload,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def list_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        user_id: Optional[str] = None,
        user_ids: Optional[List[str]] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[List[AuditLog], int]:
        query = select(AuditLog)
        count_query = select(func.count()).select_from(AuditLog)

        if user_ids is not None:
            # escopo de equipe: filtra por lista de IDs
            query = query.where(AuditLog.user_id.in_(user_ids))
            count_query = count_query.where(AuditLog.user_id.in_(user_ids))
        elif user_id:
            query = query.where(AuditLog.user_id == user_id)
            count_query = count_query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)
        if resource:
            query = query.where(AuditLog.resource == resource)
            count_query = count_query.where(AuditLog.resource == resource)
        if date_from:
            query = query.where(AuditLog.created_at >= date_from)
            count_query = count_query.where(AuditLog.created_at >= date_from)
        if date_to:
            query = query.where(AuditLog.created_at <= date_to)
            count_query = count_query.where(AuditLog.created_at <= date_to)

        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        return logs, total
