"""
Repository de consulta à tabela final_visao_cliente.

READ-ONLY — a Integration API nunca escreve nesta tabela.
Quem popula é o ETL (implementation).
"""
from typing import Optional, List, Tuple
from datetime import date

from sqlalchemy import select, func, cast, Numeric, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visao_cliente import VisaoCliente


class VisaoClienteRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Busca individual ─────────────────────────────────────────────────────

    async def get_by_cnpj(self, cd_cpf_cnpj_cliente: str) -> Optional[VisaoCliente]:
        """Busca cliente por CPF/CNPJ (chave primária)."""
        result = await self.db.execute(
            select(VisaoCliente).where(
                VisaoCliente.cd_cpf_cnpj_cliente == cd_cpf_cnpj_cliente
            )
        )
        return result.scalar_one_or_none()

    async def search_by_name(
        self,
        nome: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[VisaoCliente], int]:
        """Busca clientes por nome (case-insensitive, partial match)."""
        pattern = f"%{nome.upper()}%"
        query = select(VisaoCliente).where(
            func.upper(VisaoCliente.nome_cliente).like(pattern)
        )
        count_query = select(func.count()).select_from(VisaoCliente).where(
            func.upper(VisaoCliente.nome_cliente).like(pattern)
        )

        query = query.order_by(VisaoCliente.nome_cliente).offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        return items, total

    async def search(
        self,
        q: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[VisaoCliente], int]:
        """Busca por CPF/CNPJ ou nome."""
        query = select(VisaoCliente)
        count_q = select(func.count()).select_from(VisaoCliente)

        if q:
            pattern = f"%{q.upper()}%"
            condition = or_(
                VisaoCliente.cd_cpf_cnpj_cliente.ilike(f"%{q}%"),
                func.upper(VisaoCliente.nome_cliente).like(pattern),
            )
            query = query.where(condition)
            count_q = count_q.where(condition)

        query = query.order_by(VisaoCliente.nome_cliente).offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_result = await self.db.execute(count_q)
        total = count_result.scalar_one()

        return items, total

    # ─── Indicadores (queries dos 4 KPIs) ────────────────────────────────────

    async def count_contas_abertas(self, date_start: date, date_end: date) -> int:
        """
        Contas PJ abertas no período.
        SELECT COUNT(*) WHERE tipo_pessoa='PJ' AND status_cc='LIBERADA'
        AND dt_conta_criada BETWEEN date_start AND date_end
        """
        start_str = date_start.strftime("%Y-%m-%d")
        end_str = date_end.strftime("%Y-%m-%d")

        result = await self.db.execute(
            select(func.count()).select_from(VisaoCliente).where(
                VisaoCliente.tipo_pessoa == "PJ",
                VisaoCliente.status_cc == "LIBERADA",
                VisaoCliente.dt_conta_criada >= start_str,
                VisaoCliente.dt_conta_criada <= end_str,
            )
        )
        return result.scalar_one()

    async def count_qualificacao_c6pay(self, install_start: date, install_end: date) -> int:
        """
        C6Pay qualificados: instalados no período, sem cancelamento e TPV m0 >= 5000.
        """
        start_str = install_start.strftime("%Y-%m-%d")
        end_str = install_end.strftime("%Y-%m-%d")

        result = await self.db.execute(
            select(func.count()).select_from(VisaoCliente).where(
                VisaoCliente.tipo_pessoa == "PJ",
                VisaoCliente.status_cc == "LIBERADA",
                VisaoCliente.dt_install_maq >= start_str,
                VisaoCliente.dt_install_maq <= end_str,
                or_(
                    VisaoCliente.dt_cancelamento_maq.is_(None),
                    VisaoCliente.dt_cancelamento_maq == "",
                ),
                cast(VisaoCliente.tpv_m0, Numeric) >= 5000,
            )
        )
        return result.scalar_one()

    async def count_instalacao_c6pay(self, date_start: date, date_end: date) -> int:
        """
        C6Pay instalados no período.
        """
        start_str = date_start.strftime("%Y-%m-%d")
        end_str = date_end.strftime("%Y-%m-%d")

        result = await self.db.execute(
            select(func.count()).select_from(VisaoCliente).where(
                VisaoCliente.tipo_pessoa == "PJ",
                VisaoCliente.status_cc == "LIBERADA",
                VisaoCliente.dt_install_maq >= start_str,
                VisaoCliente.dt_install_maq <= end_str,
            )
        )
        return result.scalar_one()

    async def count_contas_qualificadas(self) -> int:
        """
        Contas qualificadas para comissão no mês corrente.
        fl_qualificado_comiss = '1' (aceita também '1.0' — artefato Excel antes do fix ETL)
        """
        result = await self.db.execute(
            select(func.count()).select_from(VisaoCliente).where(
                VisaoCliente.fl_qualificado_comiss.in_(["1", "1.0"])
            )
        )
        return result.scalar_one()
