def test_integration_owned_models_use_integration_schema():
    from app.models.user import User
    from app.models.refresh_token import RefreshToken
    from app.models.password_reset_token import PasswordResetToken
    from app.models.audit_log import AuditLog
    from app.models.crm_event import CrmInboundEvent, CrmOutboundJob

    for model in [User, RefreshToken, PasswordResetToken, AuditLog,
                  CrmInboundEvent, CrmOutboundJob]:
        assert model.__table__.schema == "integration", (
            f"{model.__name__} must have schema='integration', got: {model.__table__.schema}"
        )


def test_etl_read_only_models_use_etl_schema():
    from app.models.visao_cliente import VisaoCliente
    from app.models.visao_cliente_change_history import VisaoClienteChangeHistory
    from app.models.etl_file import EtlFile

    for model in [VisaoCliente, VisaoClienteChangeHistory, EtlFile]:
        assert model.__table__.schema == "etl", (
            f"{model.__name__} must have schema='etl', got: {model.__table__.schema}"
        )


def test_integration_foreign_keys_are_schema_qualified():
    """ForeignKey strings in integration models must use 'integration.<table>' format."""
    from sqlalchemy import inspect as sa_inspect
    from app.models.user import User
    from app.models.refresh_token import RefreshToken
    from app.models.password_reset_token import PasswordResetToken
    from app.models.audit_log import AuditLog

    expected_fks = {
        "User": {"integration.users.id"},          # gestor_id (self-referential)
        "RefreshToken": {"integration.users.id"},
        "PasswordResetToken": {"integration.users.id"},
        "AuditLog": {"integration.users.id"},
    }
    for model_cls in [User, RefreshToken, PasswordResetToken, AuditLog]:
        mapper = sa_inspect(model_cls)
        actual = {
            fk.target_fullname
            for col in mapper.columns
            for fk in col.foreign_keys
        }
        assert actual == expected_fks[model_cls.__name__], (
            f"{model_cls.__name__} FK mismatch: {actual}"
        )
