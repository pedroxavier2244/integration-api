"""
Configuração global de testes.

- Banco SQLite em memória (StaticPool) para isolamento e velocidade
- Fixtures de sessão, usuário admin, tokens de acesso
- Override da dependência get_db para usar DB de teste
"""
import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

# ─── Configura variáveis de ambiente ANTES de qualquer import da app ─────────
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32chars!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SMTP_USER", "test@test.com")
os.environ.setdefault("SMTP_PASSWORD", "testpass")
os.environ.setdefault("SMTP_FROM", "test@test.com")

# ─── Imports da app (após env vars) ──────────────────────────────────────────
from app.models.base import Base  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.models.refresh_token import RefreshToken  # noqa: E402
from app.models.password_reset_token import PasswordResetToken  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402
from app.models.crm_event import CrmInboundEvent, CrmOutboundJob  # noqa: E402
from app.models.etl_file import EtlFile  # noqa: E402
from app.models.visao_cliente import VisaoCliente  # noqa: E402
from app.models.visao_cliente_change_history import VisaoClienteChangeHistory  # noqa: E402
from app.core.security import hash_password, create_access_token  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


# ─── Engine e Session de teste (SQLite in-memory) ─────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Cria todas as tabelas antes da sessão de testes."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Sessão de banco isolada por teste com rollback automático."""
    async with engine_test.begin() as conn:
        # Cria uma transação aninhada para rollback após cada teste
        async with TestingSessionLocal(bind=conn) as session:
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP assíncrono com override do banco de teste."""

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ─── Fixtures de usuários ─────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    """Cria e persiste um usuário admin para os testes."""
    user = User(
        email="admin@test.com",
        full_name="Admin Test",
        role=UserRole.admin,
        hashed_password=hash_password("Admin@123"),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def gestor_user(db: AsyncSession) -> User:
    """Cria e persiste um usuário gestor."""
    user = User(
        email="gestor@test.com",
        full_name="Gestor Test",
        role=UserRole.gestor,
        hashed_password=hash_password("Gestor@123"),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest_asyncio.fixture
async def operador_user(db: AsyncSession) -> User:
    """Cria e persiste um usuário operador."""
    user = User(
        email="operador@test.com",
        full_name="Operador Test",
        role=UserRole.operador,
        hashed_password=hash_password("Operador@123"),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


# ─── Fixtures de tokens ───────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def admin_token(admin_user: User) -> str:
    """Token de acesso JWT para o usuário admin."""
    return create_access_token(admin_user.id, admin_user.email, admin_user.role)


@pytest_asyncio.fixture
async def gestor_token(gestor_user: User) -> str:
    """Token de acesso JWT para o usuário gestor."""
    return create_access_token(gestor_user.id, gestor_user.email, gestor_user.role)


@pytest_asyncio.fixture
async def operador_token(operador_user: User) -> str:
    """Token de acesso JWT para o usuário operador."""
    return create_access_token(operador_user.id, operador_user.email, operador_user.role)


# ─── Fixtures de dados ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def sample_cliente(db: AsyncSession) -> VisaoCliente:
    """Cria um cliente de exemplo na tabela final_visao_cliente."""
    cliente = VisaoCliente(
        cd_cpf_cnpj_cliente="12345678000195",
        nome_cliente="EMPRESA TESTE LTDA",
        tipo_pessoa="PJ",
        status_cc="LIBERADA",
        fl_qualificado_comiss="1",
        ja_recebeu_comissao="SIM",
        tpv_m0="6000.00",
        dt_conta_criada="2025-01-15",
        dt_install_maq="2025-02-01",
        uf="SP",
        ramo_atuacao="VAREJO",
    )
    db.add(cliente)
    await db.flush()
    return cliente


@pytest_asyncio.fixture
async def admin_refresh_token(db: AsyncSession, admin_user: User) -> str:
    """Cria e persiste um refresh token para o admin."""
    from app.core.security import create_refresh_token
    raw_token = create_refresh_token(admin_user.id)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    rt = RefreshToken(
        user_id=admin_user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(rt)
    await db.flush()
    return raw_token
