"""
Repository de consulta à tabela final_visao_cliente.

READ-ONLY — a Integration API nunca escreve nesta tabela.
Quem popula é o ETL (implementation).
"""
from typing import Optional, List, Tuple
from datetime import date

from sqlalchemy import select, func, cast, Numeric, or_, and_, not_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.etl_file import EtlFile
from app.models.visao_cliente import VisaoCliente
from app.models.visao_cliente_change_history import VisaoClienteChangeHistory


class VisaoClienteRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _contains(column, value: str):
        pattern = f"%{value.strip().upper()}%"
        return func.upper(func.coalesce(column, "")).like(pattern)

    @staticmethod
    def _boletos_condition(value: str):
        pattern = f"%{value.strip()}%"
        return or_(
            VisaoCliente.fl_bolcob_cadastrado.ilike(pattern),
            VisaoCliente.qtd_bolcob_emtd_mtd.ilike(pattern),
            VisaoCliente.vl_bolcob_emtd_mtd.ilike(pattern),
            VisaoCliente.qtd_bolcob_liq_mtd.ilike(pattern),
            VisaoCliente.vl_bolcob_liq_mtd.ilike(pattern),
        )

    @staticmethod
    def _never_qualificou_condition():
        # ja_recebeu_comissao foi removida do ETL — filtro baseado apenas em fl_qualificado_comiss
        return or_(
            VisaoCliente.fl_qualificado_comiss.is_(None),
            not_(VisaoCliente.fl_qualificado_comiss.in_(["1", "1.0"])),
        )

    # ─── Busca individual ─────────────────────────────────────────────────────

    async def get_by_cnpj(self, cd_cpf_cnpj_cliente: str) -> Optional[VisaoCliente]:
        """Busca cliente por CPF/CNPJ (chave primária)."""
        result = await self.db.execute(
            select(VisaoCliente).where(
                VisaoCliente.cd_cpf_cnpj_cliente == cd_cpf_cnpj_cliente
            )
        )
        return result.scalar_one_or_none()

    async def get_by_documentos(
        self,
        documentos: List[str],
        uf: Optional[str] = None,
        status_cc: Optional[str] = None,
        ramo_atuacao: Optional[str] = None,
        consultor: Optional[str] = None,
    ) -> List[VisaoCliente]:
        """Busca em lote por lista de CPF/CNPJ com filtros opcionais (AND)."""
        query = select(VisaoCliente).where(
            VisaoCliente.cd_cpf_cnpj_cliente.in_(documentos)
        )
        filters = []

        if uf:
            filters.append(
                func.upper(func.coalesce(VisaoCliente.uf, "")) == uf.strip().upper()
            )

        if status_cc:
            filters.append(
                func.upper(func.coalesce(VisaoCliente.status_cc, "")) == status_cc.strip().upper()
            )

        if ramo_atuacao:
            filters.append(self._contains(VisaoCliente.ramo_atuacao, ramo_atuacao))

        if consultor:
            pattern = f"%{consultor.strip().upper()}%"
            filters.append(or_(
                func.upper(func.coalesce(VisaoCliente.nome_consultor, "")).like(pattern),
                VisaoCliente.cd_cpf_cnpj_consultor.ilike(f"%{consultor.strip()}%"),
            ))

        if filters:
            query = query.where(*filters)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_change_history(
        self,
        documento: str,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[list[dict], int]:
        query = (
            select(
                VisaoClienteChangeHistory.id,
                VisaoClienteChangeHistory.data_base,
                VisaoClienteChangeHistory.changed_at,
                VisaoClienteChangeHistory.etl_job_id,
                VisaoClienteChangeHistory.file_id,
                EtlFile.file_date,
                EtlFile.filename,
                VisaoClienteChangeHistory.change_type,
                VisaoClienteChangeHistory.field_name,
                VisaoClienteChangeHistory.old_value,
                VisaoClienteChangeHistory.new_value,
            )
            .select_from(VisaoClienteChangeHistory)
            .outerjoin(EtlFile, EtlFile.id == VisaoClienteChangeHistory.file_id)
            .where(VisaoClienteChangeHistory.documento == documento)
            .order_by(
                VisaoClienteChangeHistory.changed_at.asc().nulls_last(),
                VisaoClienteChangeHistory.id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(VisaoClienteChangeHistory)
            .where(VisaoClienteChangeHistory.documento == documento)
        )

        result = await self.db.execute(query)
        items = [dict(row) for row in result.mappings().all()]

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        return items, total

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
        cnpj: Optional[str] = None,
        nome: Optional[str] = None,
        safra_maquina: Optional[str] = None,
        nunca_qualificou: Optional[bool] = None,
        comissao_prox_mes: Optional[str] = None,
        apuracao_comiss: Optional[str] = None,
        criterios_atingidos_comiss: Optional[str] = None,
        chaves_pix_forte: Optional[str] = None,
        cancelamento_maq: Optional[str] = None,
        m2_dias_faltantes: Optional[str] = None,
        boletos: Optional[str] = None,
        fl_bolcob_cadastrado: Optional[str] = None,
        criterio_proximo: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Tuple[List[VisaoCliente], int]:
        """Busca por CPF/CNPJ ou nome."""
        query = select(VisaoCliente)
        count_q = select(func.count()).select_from(VisaoCliente)
        filters = []

        if q:
            condition = or_(
                VisaoCliente.cd_cpf_cnpj_cliente.ilike(f"%{q}%"),
                self._contains(VisaoCliente.nome_cliente, q),
            )
            filters.append(condition)

        if cnpj:
            filters.append(VisaoCliente.cd_cpf_cnpj_cliente.ilike(f"%{cnpj.strip()}%"))

        if nome:
            filters.append(self._contains(VisaoCliente.nome_cliente, nome))

        if safra_maquina:
            pass  # coluna removida do ETL — filtro desabilitado

        if nunca_qualificou is not None:
            condition = self._never_qualificou_condition()
            filters.append(condition if nunca_qualificou else not_(condition))

        if comissao_prox_mes:
            pass  # coluna removida do ETL — filtro desabilitado

        if apuracao_comiss:
            filters.append(self._contains(VisaoCliente.apuracao_comiss, apuracao_comiss))

        if criterios_atingidos_comiss:
            filters.append(
                self._contains(
                    VisaoCliente.criterios_atingidos_comiss,
                    criterios_atingidos_comiss,
                )
            )

        if chaves_pix_forte:
            filters.append(self._contains(VisaoCliente.chaves_pix_forte, chaves_pix_forte))

        if cancelamento_maq:
            pass  # coluna removida do ETL — filtro desabilitado

        if m2_dias_faltantes:
            pass  # coluna removida do ETL — filtro desabilitado

        if boletos:
            filters.append(self._boletos_condition(boletos))

        if fl_bolcob_cadastrado:
            filters.append(
                self._contains(VisaoCliente.fl_bolcob_cadastrado, fl_bolcob_cadastrado)
            )

        if criterio_proximo:
            filters.append(self._contains(VisaoCliente.criterio_proximo, criterio_proximo))

        if filters:
            query = query.where(*filters)
            count_q = count_q.where(*filters)

        resolved_offset = offset if offset is not None else (page - 1) * page_size
        resolved_limit = limit if limit is not None else page_size

        query = query.order_by(VisaoCliente.nome_cliente).offset(resolved_offset).limit(resolved_limit)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_result = await self.db.execute(count_q)
        total = count_result.scalar_one()

        return items, total

    async def search_empresas(
        self,
        q: Optional[str] = None,
        uf: Optional[str] = None,
        status_cc: Optional[str] = None,
        ramo_atuacao: Optional[str] = None,
        consultor: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[VisaoCliente], int]:
        """Busca empresas com filtros operacionais de carteira."""
        query = select(VisaoCliente)
        count_q = select(func.count()).select_from(VisaoCliente)
        filters = []

        if q:
            filters.append(or_(
                VisaoCliente.cd_cpf_cnpj_cliente.ilike(f"%{q}%"),
                self._contains(VisaoCliente.nome_cliente, q),
            ))

        if uf:
            filters.append(
                func.upper(func.coalesce(VisaoCliente.uf, "")) == uf.strip().upper()
            )

        if status_cc:
            filters.append(
                func.upper(func.coalesce(VisaoCliente.status_cc, "")) == status_cc.strip().upper()
            )

        if ramo_atuacao:
            filters.append(self._contains(VisaoCliente.ramo_atuacao, ramo_atuacao))

        if consultor:
            pattern = f"%{consultor.strip().upper()}%"
            filters.append(or_(
                func.upper(func.coalesce(VisaoCliente.nome_consultor, "")).like(pattern),
                VisaoCliente.cd_cpf_cnpj_consultor.ilike(f"%{consultor.strip()}%"),
            ))

        if filters:
            query = query.where(*filters)
            count_q = count_q.where(*filters)

        query = (
            query.order_by(VisaoCliente.nome_cliente)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

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
