"""
Integration tests for user management endpoints.
"""
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole


BASE = "/api/v1/users"


class TestCreateUser:
    @patch("app.integrations.email_client.send_invite_email", new_callable=AsyncMock)
    async def test_admin_can_create_gestor(
        self,
        mock_send,
        client: AsyncClient,
        admin_token: str,
    ):
        resp = await client.post(
            f"{BASE}/",
            json={
                "email": "novo-gestor@test.com",
                "full_name": "Novo Gestor",
                "role": "gestor",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["role"] == "gestor"
        assert data["gestor_id"] is None
        mock_send.assert_called_once()

    @patch("app.integrations.email_client.send_invite_email", new_callable=AsyncMock)
    async def test_admin_can_create_operator_assigned_to_gestor(
        self,
        mock_send,
        client: AsyncClient,
        admin_token: str,
        gestor_user: User,
    ):
        resp = await client.post(
            f"{BASE}/",
            json={
                "email": "novo-operador@test.com",
                "full_name": "Novo Operador",
                "role": "operador",
                "gestor_id": gestor_user.id,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["role"] == "operador"
        assert data["gestor_id"] == gestor_user.id
        mock_send.assert_called_once()

    @patch("app.integrations.email_client.send_invite_email", new_callable=AsyncMock)
    async def test_gestor_can_create_operator_for_own_team(
        self,
        mock_send,
        client: AsyncClient,
        gestor_token: str,
        gestor_user: User,
    ):
        resp = await client.post(
            f"{BASE}/",
            json={
                "email": "time-gestor@test.com",
                "full_name": "Operador do Gestor",
                "role": "operador",
            },
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["role"] == "operador"
        assert data["gestor_id"] == gestor_user.id
        mock_send.assert_called_once()

    @patch("app.integrations.email_client.send_invite_email", new_callable=AsyncMock)
    async def test_gestor_cannot_create_admin_or_gestor(
        self,
        mock_send,
        client: AsyncClient,
        gestor_token: str,
    ):
        for role in ("admin", "gestor"):
            resp = await client.post(
                f"{BASE}/",
                json={
                    "email": f"{role}@test.com",
                    "full_name": f"Novo {role}",
                    "role": role,
                },
                headers={"Authorization": f"Bearer {gestor_token}"},
            )
            assert resp.status_code == 403
        mock_send.assert_not_called()

    @patch("app.integrations.email_client.send_invite_email", new_callable=AsyncMock)
    async def test_gestor_cannot_create_operator_for_other_gestor(
        self,
        mock_send,
        client: AsyncClient,
        gestor_token: str,
        admin_token: str,
    ):
        other_gestor = await self._create_user(
            client,
            admin_token,
            email="other-gestor@test.com",
            full_name="Other Gestor",
            role="gestor",
        )
        mock_send.reset_mock()

        resp = await client.post(
            f"{BASE}/",
            json={
                "email": "operador-outro-time@test.com",
                "full_name": "Operador Outro Time",
                "role": "operador",
                "gestor_id": other_gestor["id"],
            },
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 403
        mock_send.assert_not_called()

    async def test_create_user_forbidden_for_operador(
        self,
        client: AsyncClient,
        operador_token: str,
    ):
        resp = await client.post(
            f"{BASE}/",
            json={
                "email": "x@test.com",
                "full_name": "X",
                "role": "operador",
            },
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 403

    @staticmethod
    async def _create_user(
        client: AsyncClient,
        token: str,
        *,
        email: str,
        full_name: str,
        role: str,
    ) -> dict:
        with patch("app.integrations.email_client.send_invite_email", new_callable=AsyncMock):
            resp = await client.post(
                f"{BASE}/",
                json={"email": email, "full_name": full_name, "role": role},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 201
        return resp.json()


class TestListUsers:
    async def test_admin_lists_all_users(
        self,
        client: AsyncClient,
        admin_token: str,
        admin_user: User,
        gestor_user: User,
        operador_user: User,
        operador_sem_gestor_user: User,
    ):
        resp = await client.get(
            f"{BASE}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        ids = {item["id"] for item in data["items"]}
        assert admin_user.id in ids
        assert gestor_user.id in ids
        assert operador_user.id in ids
        assert operador_sem_gestor_user.id in ids

    async def test_gestor_lists_only_own_team(
        self,
        client: AsyncClient,
        gestor_token: str,
        gestor_user: User,
        operador_user: User,
        operador_sem_gestor_user: User,
        admin_user: User,
    ):
        resp = await client.get(
            f"{BASE}/",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        ids = {item["id"] for item in data["items"]}
        assert operador_user.id in ids
        assert admin_user.id not in ids
        assert gestor_user.id not in ids
        assert operador_sem_gestor_user.id not in ids
        assert all(item["role"] == "operador" for item in data["items"])


class TestGetUser:
    async def test_admin_can_get_any_user(
        self,
        client: AsyncClient,
        admin_token: str,
        gestor_user: User,
    ):
        resp = await client.get(
            f"{BASE}/{gestor_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == gestor_user.id

    async def test_gestor_can_get_own_operator(
        self,
        client: AsyncClient,
        gestor_token: str,
        operador_user: User,
    ):
        resp = await client.get(
            f"{BASE}/{operador_user.id}",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == operador_user.id

    async def test_gestor_cannot_get_admin_or_unassigned_operator(
        self,
        client: AsyncClient,
        gestor_token: str,
        admin_user: User,
        operador_sem_gestor_user: User,
    ):
        for user_id in (admin_user.id, operador_sem_gestor_user.id):
            resp = await client.get(
                f"{BASE}/{user_id}",
                headers={"Authorization": f"Bearer {gestor_token}"},
            )
            assert resp.status_code == 403


class TestUpdateUser:
    async def test_admin_can_assign_operator_to_gestor(
        self,
        client: AsyncClient,
        admin_token: str,
        gestor_user: User,
        operador_sem_gestor_user: User,
    ):
        resp = await client.patch(
            f"{BASE}/{operador_sem_gestor_user.id}",
            json={"gestor_id": gestor_user.id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["gestor_id"] == gestor_user.id

    async def test_admin_can_promote_operator_and_clear_team(
        self,
        client: AsyncClient,
        admin_token: str,
        operador_user: User,
    ):
        resp = await client.patch(
            f"{BASE}/{operador_user.id}",
            json={"role": "gestor"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "gestor"
        assert data["gestor_id"] is None

    async def test_gestor_can_update_own_operator_name(
        self,
        client: AsyncClient,
        gestor_token: str,
        operador_user: User,
    ):
        resp = await client.patch(
            f"{BASE}/{operador_user.id}",
            json={"full_name": "Operador Atualizado"},
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Operador Atualizado"

    async def test_gestor_can_claim_unassigned_operator(
        self,
        client: AsyncClient,
        gestor_token: str,
        gestor_user: User,
        operador_sem_gestor_user: User,
    ):
        resp = await client.patch(
            f"{BASE}/{operador_sem_gestor_user.id}",
            json={"gestor_id": gestor_user.id},
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["gestor_id"] == gestor_user.id

    async def test_gestor_can_remove_operator_from_team(
        self,
        client: AsyncClient,
        gestor_token: str,
        operador_user: User,
    ):
        resp = await client.patch(
            f"{BASE}/{operador_user.id}",
            json={"gestor_id": None},
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["gestor_id"] is None

    async def test_gestor_cannot_promote_operator(
        self,
        client: AsyncClient,
        gestor_token: str,
        operador_user: User,
    ):
        resp = await client.patch(
            f"{BASE}/{operador_user.id}",
            json={"role": "gestor"},
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 403

    async def test_gestor_cannot_manage_other_team_operator(
        self,
        client: AsyncClient,
        db: AsyncSession,
        gestor_token: str,
    ):
        other_gestor = User(
            email="other-team-gestor@test.com",
            full_name="Other Team Gestor",
            role=UserRole.gestor,
            hashed_password=hash_password("Gestor@123"),
            is_active=True,
        )
        db.add(other_gestor)
        await db.flush()

        other_operator = User(
            email="other-team-operador@test.com",
            full_name="Other Team Operador",
            role=UserRole.operador,
            gestor_id=other_gestor.id,
            hashed_password=hash_password("Operador@123"),
            is_active=True,
        )
        db.add(other_operator)
        await db.flush()

        resp = await client.patch(
            f"{BASE}/{other_operator.id}",
            json={"full_name": "Tentativa Invalida"},
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 403


class TestDeactivateUser:
    async def test_admin_can_deactivate_any_non_self_user(
        self,
        client: AsyncClient,
        db: AsyncSession,
        admin_token: str,
    ):
        user = User(
            email="to-deactivate@test.com",
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
        assert resp.json()["success"] is True

    async def test_gestor_can_deactivate_own_operator(
        self,
        client: AsyncClient,
        gestor_token: str,
        operador_user: User,
    ):
        resp = await client.delete(
            f"{BASE}/{operador_user.id}",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 200

    async def test_gestor_cannot_deactivate_outside_team(
        self,
        client: AsyncClient,
        gestor_token: str,
        admin_user: User,
    ):
        resp = await client.delete(
            f"{BASE}/{admin_user.id}",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 403


class TestRevokeSessions:
    async def test_gestor_can_revoke_sessions_of_own_operator(
        self,
        client: AsyncClient,
        gestor_token: str,
        operador_user: User,
    ):
        resp = await client.post(
            f"{BASE}/{operador_user.id}/revoke-sessions",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_gestor_cannot_revoke_sessions_outside_team(
        self,
        client: AsyncClient,
        gestor_token: str,
        admin_user: User,
    ):
        resp = await client.post(
            f"{BASE}/{admin_user.id}/revoke-sessions",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 403


class TestResendInvite:
    @patch("app.integrations.email_client.send_invite_email", new_callable=AsyncMock)
    async def test_gestor_can_resend_invite_for_own_operator_without_password(
        self,
        mock_send,
        client: AsyncClient,
        db: AsyncSession,
        gestor_token: str,
        gestor_user: User,
    ):
        user = User(
            email="noinvite@test.com",
            full_name="No Invite",
            role=UserRole.operador,
            gestor_id=gestor_user.id,
            hashed_password=None,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        resp = await client.post(
            f"{BASE}/{user.id}/resend-invite",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_send.assert_called_once()

    async def test_gestor_cannot_resend_invite_outside_team(
        self,
        client: AsyncClient,
        gestor_token: str,
        admin_user: User,
    ):
        resp = await client.post(
            f"{BASE}/{admin_user.id}/resend-invite",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 403
