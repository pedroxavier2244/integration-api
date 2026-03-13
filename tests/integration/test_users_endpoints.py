"""
Testes de integração para os endpoints de usuários.

POST   /api/v1/users/
GET    /api/v1/users/
GET    /api/v1/users/{id}
PATCH  /api/v1/users/{id}
DELETE /api/v1/users/{id}
POST   /api/v1/users/{id}/revoke-sessions
POST   /api/v1/users/{id}/resend-invite
"""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.core.security import hash_password


BASE = "/api/v1/users"


class TestCreateUser:
    @patch("app.integrations.email_client.send_invite_email", new_callable=AsyncMock)
    async def test_create_user_success(self, mock_send, client: AsyncClient, admin_token: str):
        resp = await client.post(
            f"{BASE}/",
            json={"email": "novo@test.com", "full_name": "Novo Usuário", "role": "operador"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "novo@test.com"
        assert data["role"] == "operador"
        assert data["invite_sent"] is True
        mock_send.assert_called_once()

    @patch("app.integrations.email_client.send_invite_email", new_callable=AsyncMock)
    async def test_create_user_duplicate_email(self, mock_send, client: AsyncClient, admin_token: str, admin_user: User):
        resp = await client.post(
            f"{BASE}/",
            json={"email": "admin@test.com", "full_name": "Duplicado", "role": "gestor"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409

    async def test_create_user_forbidden_for_operador(self, client: AsyncClient, operador_token: str):
        resp = await client.post(
            f"{BASE}/",
            json={"email": "x@test.com", "full_name": "X", "role": "operador"},
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 403

    async def test_create_user_invalid_role(self, client: AsyncClient, admin_token: str):
        resp = await client.post(
            f"{BASE}/",
            json={"email": "x@test.com", "full_name": "X", "role": "superadmin"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    async def test_create_user_missing_name(self, client: AsyncClient, admin_token: str):
        resp = await client.post(
            f"{BASE}/",
            json={"email": "x@test.com", "role": "operador"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    async def test_create_user_without_token(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE}/",
            json={"email": "x@test.com", "full_name": "X", "role": "operador"},
        )
        assert resp.status_code == 403


class TestListUsers:
    async def test_list_users_success(self, client: AsyncClient, admin_token: str, admin_user: User):
        resp = await client.get(
            f"{BASE}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_list_users_pagination(self, client: AsyncClient, admin_token: str, admin_user: User):
        resp = await client.get(
            f"{BASE}/?page=1&page_size=5",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    async def test_list_users_forbidden_for_gestor(self, client: AsyncClient, gestor_token: str):
        resp = await client.get(
            f"{BASE}/",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 403


class TestGetUser:
    async def test_get_user_success(self, client: AsyncClient, admin_token: str, admin_user: User):
        resp = await client.get(
            f"{BASE}/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == admin_user.id
        assert data["email"] == "admin@test.com"

    async def test_get_user_not_found(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            f"{BASE}/nonexistent-id",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    async def test_get_user_without_auth(self, client: AsyncClient, admin_user: User):
        resp = await client.get(f"{BASE}/{admin_user.id}")
        assert resp.status_code == 403


class TestUpdateUser:
    async def test_update_user_name_success(self, client: AsyncClient, admin_token: str, operador_user: User):
        resp = await client.patch(
            f"{BASE}/{operador_user.id}",
            json={"full_name": "Novo Nome Operador"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Novo Nome Operador"

    async def test_update_user_role_success(self, client: AsyncClient, admin_token: str, operador_user: User):
        resp = await client.patch(
            f"{BASE}/{operador_user.id}",
            json={"role": "gestor"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "gestor"

    async def test_update_user_not_found(self, client: AsyncClient, admin_token: str):
        resp = await client.patch(
            f"{BASE}/nonexistent-id",
            json={"full_name": "Nome"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    async def test_update_user_forbidden(self, client: AsyncClient, operador_token: str, admin_user: User):
        resp = await client.patch(
            f"{BASE}/{admin_user.id}",
            json={"full_name": "Hack"},
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 403


class TestDeactivateUser:
    async def test_deactivate_user_success(self, client: AsyncClient, db: AsyncSession, admin_token: str):
        # Cria usuário para desativar (não pode ser o próprio admin)
        user = User(
            email="todeactivate@test.com",
            full_name="To Deactivate",
            role=UserRole.operador,
            hashed_password=hash_password("pass"),
            is_active=True,
        )
        db.add(user)
        await db.flush()

        resp = await client.delete(
            f"{BASE}/{user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    async def test_cannot_deactivate_self(self, client: AsyncClient, admin_token: str, admin_user: User):
        resp = await client.delete(
            f"{BASE}/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 403

    async def test_deactivate_not_found(self, client: AsyncClient, admin_token: str):
        resp = await client.delete(
            f"{BASE}/nonexistent-id",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


class TestRevokeSessions:
    async def test_revoke_sessions_success(self, client: AsyncClient, admin_token: str, operador_user: User):
        resp = await client.post(
            f"{BASE}/{operador_user.id}/revoke-sessions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    async def test_revoke_sessions_not_found(self, client: AsyncClient, admin_token: str):
        resp = await client.post(
            f"{BASE}/nonexistent-id/revoke-sessions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


class TestResendInvite:
    @patch("app.integrations.email_client.send_invite_email", new_callable=AsyncMock)
    async def test_resend_invite_success(self, mock_send, client: AsyncClient, db: AsyncSession, admin_token: str):
        # Usuário sem senha (não aceitou convite ainda)
        user = User(
            email="noinvite@test.com",
            full_name="No Invite",
            role=UserRole.operador,
            hashed_password=None,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        resp = await client.post(
            f"{BASE}/{user.id}/resend-invite",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        mock_send.assert_called_once()

    async def test_resend_invite_already_accepted(self, client: AsyncClient, admin_token: str, operador_user: User):
        """Usuário que já definiu senha não pode receber novo convite."""
        resp = await client.post(
            f"{BASE}/{operador_user.id}/resend-invite",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 409

    async def test_resend_invite_not_found(self, client: AsyncClient, admin_token: str):
        resp = await client.post(
            f"{BASE}/nonexistent-id/resend-invite",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
