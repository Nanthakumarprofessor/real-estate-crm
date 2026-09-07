"""
Phase 4 — User Management API tests.

Covers all 36 required cases plus additional edge cases:

Authorization (1–11):
  1.  Admin can list users
  2.  Sales cannot list users → 403
  3.  Unauthenticated request → 401
  4.  Admin can create user
  5.  Sales cannot create user → 403
  6.  Admin can view user
  7.  Sales cannot view user → 403
  8.  Admin can update user
  9.  Sales cannot update user → 403
  10. Admin can deactivate user
  11. Sales cannot deactivate user → 403

Creation (12–17):
  12. Create Admin user
  13. Create Sales user
  14. Duplicate email → 409
  15. Email is normalized to lowercase
  16. Password is bcrypt hashed in DB
  17. Password hash never returned

Retrieval (18–23):
  18. Existing user → 200
  19. Non-existent user → 404
  20. User list pagination works
  21. Search by name/email works
  22. Role filtering works
  23. Active/inactive filtering works

Update (24–28):
  24. Update name
  25. Update email
  26. Update role
  27. Update password — new password verifies correctly
  28. Duplicate email update → 409

Deactivation (29–32):
  29. Deactivate Sales user
  30. Deactivated user has is_active=false
  31. Deactivated user cannot log in
  32. Existing user data remains intact (record still exists)

Last Admin Protection (33–36):
  33. Cannot deactivate the last active Admin
  34. Cannot change last active Admin role to SALES
  35. Multiple Admins — one can be deactivated
  36. After deactivating one, another active Admin still exists

All tests use isolated test data except where seeded users are appropriate.
Tests clean up after themselves via a temporary user fixture.
"""
import warnings
import uuid

warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.main import app
from src.repository.database import SessionLocal
from src.repository.models.user import User
from src.utils.enums import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── URLs ──────────────────────────────────────────────────────────────────────
USERS_URL = "/api/users"
LOGIN_URL = "/api/auth/login"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@123"
SALES_EMAIL = "sales@example.com"
SALES_PASSWORD = "Sales@123"


# ── Shared client fixture ─────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Token helpers ─────────────────────────────────────────────────────────────
def _get_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post(LOGIN_URL, json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


def _admin_headers(client: TestClient) -> dict:
    return {"Authorization": f"Bearer {_get_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)}"}


def _sales_headers(client: TestClient) -> dict:
    return {"Authorization": f"Bearer {_get_token(client, SALES_EMAIL, SALES_PASSWORD)}"}


# ── Unique email helper ───────────────────────────────────────────────────────
def _unique_email(prefix: str = "test") -> str:
    """Generate a unique email for each test run to avoid cross-test collisions."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}@test.com"


# ── DB helpers ────────────────────────────────────────────────────────────────
def _get_user_from_db(user_id: int) -> User | None:
    db: Session = SessionLocal()
    try:
        return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    finally:
        db.close()


def _delete_user_from_db(user_id: int) -> None:
    """Hard-delete a test user to clean up after tests."""
    db: Session = SessionLocal()
    try:
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _set_user_active(email: str, active: bool) -> None:
    db: Session = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == email)).scalar_one()
        user.is_active = active
        db.commit()
    finally:
        db.close()


def _create_user_payload(
    email: str | None = None,
    role: str = "SALES",
    password: str = "Test@1234",
    name: str = "Test User",
) -> dict:
    return {
        "name": name,
        "email": email or _unique_email(),
        "password": password,
        "role": role,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 1–11  AUTHORIZATION
# ═════════════════════════════════════════════════════════════════════════════

class TestUsersAuthorization:

    # Test 1
    def test_admin_can_list_users(self, client: TestClient) -> None:
        resp = client.get(USERS_URL, headers=_admin_headers(client))
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body

    # Test 2
    def test_sales_cannot_list_users(self, client: TestClient) -> None:
        resp = client.get(USERS_URL, headers=_sales_headers(client))
        assert resp.status_code == 403

    # Test 3
    def test_unauthenticated_cannot_list_users(self, client: TestClient) -> None:
        resp = client.get(USERS_URL)
        assert resp.status_code == 401

    # Test 4
    def test_admin_can_create_user(self, client: TestClient) -> None:
        payload = _create_user_payload()
        resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 201
        created_id = resp.json()["id"]
        _delete_user_from_db(created_id)

    # Test 5
    def test_sales_cannot_create_user(self, client: TestClient) -> None:
        resp = client.post(
            USERS_URL,
            json=_create_user_payload(),
            headers=_sales_headers(client),
        )
        assert resp.status_code == 403

    # Test 6
    def test_admin_can_view_user(self, client: TestClient) -> None:
        # Use the seeded admin user (id=1 is typically the admin from seed)
        resp = client.get(USERS_URL, headers=_admin_headers(client))
        user_id = resp.json()["items"][0]["id"]
        resp2 = client.get(f"{USERS_URL}/{user_id}", headers=_admin_headers(client))
        assert resp2.status_code == 200

    # Test 7
    def test_sales_cannot_view_user(self, client: TestClient) -> None:
        resp = client.get(f"{USERS_URL}/1", headers=_sales_headers(client))
        assert resp.status_code == 403

    # Test 8
    def test_admin_can_update_user(self, client: TestClient) -> None:
        payload = _create_user_payload()
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        update_resp = client.put(
            f"{USERS_URL}/{user_id}",
            json={"name": "Updated Name"},
            headers=_admin_headers(client),
        )
        assert update_resp.status_code == 200
        _delete_user_from_db(user_id)

    # Test 9
    def test_sales_cannot_update_user(self, client: TestClient) -> None:
        resp = client.put(
            f"{USERS_URL}/1",
            json={"name": "Hacked"},
            headers=_sales_headers(client),
        )
        assert resp.status_code == 403

    # Test 10
    def test_admin_can_deactivate_user(self, client: TestClient) -> None:
        payload = _create_user_payload()
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        deact_resp = client.patch(
            f"{USERS_URL}/{user_id}/deactivate",
            headers=_admin_headers(client),
        )
        assert deact_resp.status_code == 200
        _delete_user_from_db(user_id)

    # Test 11
    def test_sales_cannot_deactivate_user(self, client: TestClient) -> None:
        resp = client.patch(
            f"{USERS_URL}/1/deactivate",
            headers=_sales_headers(client),
        )
        assert resp.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# 12–17  CREATION
# ═════════════════════════════════════════════════════════════════════════════

class TestUserCreation:

    # Test 12
    def test_create_admin_user(self, client: TestClient) -> None:
        payload = _create_user_payload(role="ADMIN")
        resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 201
        body = resp.json()
        assert body["role"] == "ADMIN"
        _delete_user_from_db(body["id"])

    # Test 13
    def test_create_sales_user(self, client: TestClient) -> None:
        payload = _create_user_payload(role="SALES")
        resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 201
        body = resp.json()
        assert body["role"] == "SALES"
        _delete_user_from_db(body["id"])

    # Test 14
    def test_duplicate_email_returns_409(self, client: TestClient) -> None:
        email = _unique_email("dup")
        payload = _create_user_payload(email=email)

        r1 = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert r1.status_code == 201
        user_id = r1.json()["id"]

        r2 = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert r2.status_code == 409

        _delete_user_from_db(user_id)

    # Test 15
    def test_email_normalized_to_lowercase(self, client: TestClient) -> None:
        mixed_email = f"UPPER_{uuid.uuid4().hex[:6]}@EXAMPLE.COM"
        payload = _create_user_payload(email=mixed_email)

        resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 201
        body = resp.json()

        assert body["email"] == mixed_email.lower()
        _delete_user_from_db(body["id"])

    # Test 16
    def test_password_is_bcrypt_hashed_in_db(self, client: TestClient) -> None:
        plain_pw = "MySecret@999"
        payload = _create_user_payload(password=plain_pw)

        resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 201
        user_id = resp.json()["id"]

        db_user = _get_user_from_db(user_id)
        assert db_user is not None
        # Must NOT be stored as plaintext
        assert db_user.password_hash != plain_pw
        # Must be a valid bcrypt hash
        assert db_user.password_hash.startswith("$2b$") or db_user.password_hash.startswith("$2a$")
        # Must verify correctly
        assert pwd_context.verify(plain_pw, db_user.password_hash)

        _delete_user_from_db(user_id)

    # Test 17
    def test_password_hash_never_returned(self, client: TestClient) -> None:
        payload = _create_user_payload()
        resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 201
        body = resp.json()

        assert "password" not in body
        assert "password_hash" not in body
        assert "hash" not in body

        _delete_user_from_db(body["id"])

    def test_create_user_missing_required_fields_returns_422(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            USERS_URL,
            json={"email": "incomplete@test.com"},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 422

    def test_create_user_invalid_role_returns_422(self, client: TestClient) -> None:
        payload = _create_user_payload()
        payload["role"] = "SUPERUSER"
        resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 422

    def test_create_user_is_active_by_default(self, client: TestClient) -> None:
        payload = _create_user_payload()
        resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 201
        assert resp.json()["is_active"] is True
        _delete_user_from_db(resp.json()["id"])


# ═════════════════════════════════════════════════════════════════════════════
# 18–23  RETRIEVAL
# ═════════════════════════════════════════════════════════════════════════════

class TestUserRetrieval:

    # Test 18
    def test_get_existing_user_returns_200(self, client: TestClient) -> None:
        # Create a user then fetch it
        payload = _create_user_payload()
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        user_id = create_resp.json()["id"]

        resp = client.get(f"{USERS_URL}/{user_id}", headers=_admin_headers(client))
        assert resp.status_code == 200
        assert resp.json()["id"] == user_id
        _delete_user_from_db(user_id)

    # Test 19
    def test_get_nonexistent_user_returns_404(self, client: TestClient) -> None:
        resp = client.get(f"{USERS_URL}/999999", headers=_admin_headers(client))
        assert resp.status_code == 404

    # Test 20
    def test_user_list_pagination(self, client: TestClient) -> None:
        resp_p1 = client.get(
            USERS_URL, params={"page": 1, "size": 1}, headers=_admin_headers(client)
        )
        assert resp_p1.status_code == 200
        body = resp_p1.json()
        assert body["page"] == 1
        assert body["size"] == 1
        assert len(body["items"]) <= 1
        # total reflects all users, not just this page
        assert body["total"] >= 1

    # Test 21
    def test_search_by_name(self, client: TestClient) -> None:
        unique_name = f"SearchableUser_{uuid.uuid4().hex[:6]}"
        payload = _create_user_payload(name=unique_name)
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        user_id = create_resp.json()["id"]

        resp = client.get(
            USERS_URL, params={"search": unique_name}, headers=_admin_headers(client)
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(u["name"] == unique_name for u in items)
        _delete_user_from_db(user_id)

    def test_search_by_email(self, client: TestClient) -> None:
        unique_email = _unique_email("searchemail")
        payload = _create_user_payload(email=unique_email)
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        user_id = create_resp.json()["id"]

        resp = client.get(
            USERS_URL, params={"search": unique_email}, headers=_admin_headers(client)
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1
        _delete_user_from_db(user_id)

    # Test 22
    def test_role_filter_returns_only_matching_role(self, client: TestClient) -> None:
        resp = client.get(
            USERS_URL, params={"role": "ADMIN"}, headers=_admin_headers(client)
        )
        assert resp.status_code == 200
        for user in resp.json()["items"]:
            assert user["role"] == "ADMIN"

    # Test 23
    def test_is_active_filter(self, client: TestClient) -> None:
        # Create a user then deactivate them
        payload = _create_user_payload()
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        user_id = create_resp.json()["id"]
        client.patch(f"{USERS_URL}/{user_id}/deactivate", headers=_admin_headers(client))

        resp_inactive = client.get(
            USERS_URL, params={"is_active": "false"}, headers=_admin_headers(client)
        )
        assert resp_inactive.status_code == 200
        for user in resp_inactive.json()["items"]:
            assert user["is_active"] is False

        resp_active = client.get(
            USERS_URL, params={"is_active": "true"}, headers=_admin_headers(client)
        )
        assert resp_active.status_code == 200
        for user in resp_active.json()["items"]:
            assert user["is_active"] is True

        _delete_user_from_db(user_id)

    def test_list_response_shape(self, client: TestClient) -> None:
        resp = client.get(USERS_URL, headers=_admin_headers(client))
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) >= {"items", "total", "page", "size"}


# ═════════════════════════════════════════════════════════════════════════════
# 24–28  UPDATE
# ═════════════════════════════════════════════════════════════════════════════

class TestUserUpdate:

    def _create_temp_user(self, client: TestClient, role: str = "SALES") -> dict:
        payload = _create_user_payload(role=role)
        resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 201
        return resp.json()

    # Test 24
    def test_update_name(self, client: TestClient) -> None:
        user = self._create_temp_user(client)
        resp = client.put(
            f"{USERS_URL}/{user['id']}",
            json={"name": "Brand New Name"},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Brand New Name"
        _delete_user_from_db(user["id"])

    # Test 25
    def test_update_email(self, client: TestClient) -> None:
        user = self._create_temp_user(client)
        new_email = _unique_email("updated")
        resp = client.put(
            f"{USERS_URL}/{user['id']}",
            json={"email": new_email},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == new_email.lower()
        _delete_user_from_db(user["id"])

    # Test 26
    def test_update_role(self, client: TestClient) -> None:
        user = self._create_temp_user(client, role="SALES")
        resp = client.put(
            f"{USERS_URL}/{user['id']}",
            json={"role": "ADMIN"},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "ADMIN"
        _delete_user_from_db(user["id"])

    # Test 27
    def test_update_password_and_new_password_works(self, client: TestClient) -> None:
        new_pw = "NewPassword@999"
        payload = _create_user_payload(password="OldPassword@123")
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        user_id = create_resp.json()["id"]
        user_email = create_resp.json()["email"]

        # Update password
        update_resp = client.put(
            f"{USERS_URL}/{user_id}",
            json={"password": new_pw},
            headers=_admin_headers(client),
        )
        assert update_resp.status_code == 200
        assert "password" not in update_resp.json()
        assert "password_hash" not in update_resp.json()

        # New password must allow login
        login_resp = client.post(
            LOGIN_URL, json={"email": user_email, "password": new_pw}
        )
        assert login_resp.status_code == 200

        # Old password must no longer work
        old_login = client.post(
            LOGIN_URL, json={"email": user_email, "password": "OldPassword@123"}
        )
        assert old_login.status_code == 401

        _delete_user_from_db(user_id)

    # Test 28
    def test_update_email_duplicate_returns_409(self, client: TestClient) -> None:
        user_a = self._create_temp_user(client)
        user_b = self._create_temp_user(client)

        # Try to update user_b's email to user_a's email
        resp = client.put(
            f"{USERS_URL}/{user_b['id']}",
            json={"email": user_a["email"]},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 409

        _delete_user_from_db(user_a["id"])
        _delete_user_from_db(user_b["id"])

    def test_update_nonexistent_user_returns_404(self, client: TestClient) -> None:
        resp = client.put(
            f"{USERS_URL}/999999",
            json={"name": "Ghost"},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 404

    def test_update_response_never_contains_password(self, client: TestClient) -> None:
        user = self._create_temp_user(client)
        resp = client.put(
            f"{USERS_URL}/{user['id']}",
            json={"name": "Safe Update"},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "password" not in body
        assert "password_hash" not in body
        _delete_user_from_db(user["id"])


# ═════════════════════════════════════════════════════════════════════════════
# 29–32  DEACTIVATION
# ═════════════════════════════════════════════════════════════════════════════

class TestUserDeactivation:

    # Test 29
    def test_deactivate_sales_user(self, client: TestClient) -> None:
        payload = _create_user_payload(role="SALES")
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        resp = client.patch(
            f"{USERS_URL}/{user_id}/deactivate",
            headers=_admin_headers(client),
        )
        assert resp.status_code == 200
        _delete_user_from_db(user_id)

    # Test 30
    def test_deactivated_user_has_is_active_false(self, client: TestClient) -> None:
        payload = _create_user_payload(role="SALES")
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        user_id = create_resp.json()["id"]

        client.patch(
            f"{USERS_URL}/{user_id}/deactivate", headers=_admin_headers(client)
        )

        # Verify via API response
        get_resp = client.get(f"{USERS_URL}/{user_id}", headers=_admin_headers(client))
        assert get_resp.json()["is_active"] is False

        # Also verify in DB directly
        db_user = _get_user_from_db(user_id)
        assert db_user is not None
        assert db_user.is_active is False

        _delete_user_from_db(user_id)

    # Test 31
    def test_deactivated_user_cannot_log_in(self, client: TestClient) -> None:
        email = _unique_email("deact_login")
        password = "Deact@1234"
        payload = _create_user_payload(email=email, password=password, role="SALES")
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        user_id = create_resp.json()["id"]

        # Confirm login works before deactivation
        pre_login = client.post(LOGIN_URL, json={"email": email, "password": password})
        assert pre_login.status_code == 200

        # Deactivate
        client.patch(
            f"{USERS_URL}/{user_id}/deactivate", headers=_admin_headers(client)
        )

        # Login must now fail
        post_login = client.post(LOGIN_URL, json={"email": email, "password": password})
        assert post_login.status_code == 401

        _delete_user_from_db(user_id)

    # Test 32
    def test_deactivated_user_record_still_exists(self, client: TestClient) -> None:
        payload = _create_user_payload(role="SALES")
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        user_id = create_resp.json()["id"]

        client.patch(
            f"{USERS_URL}/{user_id}/deactivate", headers=_admin_headers(client)
        )

        # Record must still exist in DB
        db_user = _get_user_from_db(user_id)
        assert db_user is not None, "User record was physically deleted — it should only be deactivated"
        assert db_user.is_active is False

        _delete_user_from_db(user_id)

    def test_deactivate_nonexistent_user_returns_404(self, client: TestClient) -> None:
        resp = client.patch(
            f"{USERS_URL}/999999/deactivate", headers=_admin_headers(client)
        )
        assert resp.status_code == 404

    def test_deactivate_already_inactive_user_is_idempotent(
        self, client: TestClient
    ) -> None:
        """Deactivating an already-inactive user must not raise an error."""
        payload = _create_user_payload(role="SALES")
        create_resp = client.post(USERS_URL, json=payload, headers=_admin_headers(client))
        user_id = create_resp.json()["id"]

        client.patch(f"{USERS_URL}/{user_id}/deactivate", headers=_admin_headers(client))
        resp2 = client.patch(
            f"{USERS_URL}/{user_id}/deactivate", headers=_admin_headers(client)
        )
        assert resp2.status_code == 200
        _delete_user_from_db(user_id)


# ═════════════════════════════════════════════════════════════════════════════
# 33–36  LAST ADMIN PROTECTION
# ═════════════════════════════════════════════════════════════════════════════

class TestLastAdminProtection:

    def _get_admin_id(self, client: TestClient) -> int:
        """Get the seeded admin user's ID."""
        resp = client.get(
            USERS_URL,
            params={"role": "ADMIN", "is_active": "true"},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 200
        admins = resp.json()["items"]
        assert len(admins) >= 1
        return admins[0]["id"]

    def _ensure_single_active_admin(self, client: TestClient) -> int:
        """
        Ensure exactly one active admin exists.
        Deactivates extra admins (cleanup after tests that created additional admins).
        Returns the ID of the remaining active admin.
        """
        resp = client.get(
            USERS_URL,
            params={"role": "ADMIN", "is_active": "true", "size": 100},
            headers=_admin_headers(client),
        )
        admins = resp.json()["items"]
        # Keep the first (seeded) admin, deactivate any others
        keeper_id = None
        for i, admin in enumerate(admins):
            if admin["email"] == ADMIN_EMAIL:
                keeper_id = admin["id"]
            else:
                _set_user_active(admin["email"], False)
        return keeper_id

    # Test 33
    def test_cannot_deactivate_last_active_admin(self, client: TestClient) -> None:
        """
        If only one active admin exists, deactivating them must return 400.
        The database must remain unchanged.
        """
        self._ensure_single_active_admin(client)
        admin_id = self._get_admin_id(client)

        resp = client.patch(
            f"{USERS_URL}/{admin_id}/deactivate",
            headers=_admin_headers(client),
        )
        assert resp.status_code == 400
        body = resp.json()
        assert "last" in body["detail"].lower() or "admin" in body["detail"].lower()

        # Verify DB is unchanged
        db_user = _get_user_from_db(admin_id)
        assert db_user.is_active is True

    # Test 34
    def test_cannot_change_last_active_admin_role_to_sales(
        self, client: TestClient
    ) -> None:
        """
        Changing the last active admin's role to SALES must return 400.
        """
        self._ensure_single_active_admin(client)
        admin_id = self._get_admin_id(client)

        resp = client.put(
            f"{USERS_URL}/{admin_id}",
            json={"role": "SALES"},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 400
        body = resp.json()
        assert "admin" in body["detail"].lower()

        # Verify DB unchanged
        db_user = _get_user_from_db(admin_id)
        assert db_user.role == UserRole.ADMIN

    # Test 35
    def test_can_deactivate_one_admin_when_multiple_exist(
        self, client: TestClient
    ) -> None:
        """
        When 2+ active admins exist, deactivating one must succeed.
        """
        # Create a second admin
        second_admin_payload = _create_user_payload(role="ADMIN")
        create_resp = client.post(
            USERS_URL, json=second_admin_payload, headers=_admin_headers(client)
        )
        assert create_resp.status_code == 201
        second_id = create_resp.json()["id"]

        # Now deactivate the second admin — must succeed
        deact_resp = client.patch(
            f"{USERS_URL}/{second_id}/deactivate",
            headers=_admin_headers(client),
        )
        assert deact_resp.status_code == 200
        assert deact_resp.json()["is_active"] is False
        _delete_user_from_db(second_id)

    # Test 36
    def test_one_admin_remains_after_deactivating_another(
        self, client: TestClient
    ) -> None:
        """
        After deactivating one of two admins, the other must still be active.
        """
        # Create a second admin
        second_admin_payload = _create_user_payload(role="ADMIN")
        create_resp = client.post(
            USERS_URL, json=second_admin_payload, headers=_admin_headers(client)
        )
        assert create_resp.status_code == 201
        second_id = create_resp.json()["id"]

        # Deactivate the second admin
        client.patch(
            f"{USERS_URL}/{second_id}/deactivate", headers=_admin_headers(client)
        )

        # The seeded admin must still be active
        resp = client.get(
            USERS_URL,
            params={"role": "ADMIN", "is_active": "true"},
            headers=_admin_headers(client),
        )
        active_admins = resp.json()["items"]
        assert len(active_admins) >= 1
        active_emails = [a["email"] for a in active_admins]
        assert ADMIN_EMAIL in active_emails

        _delete_user_from_db(second_id)

    def test_last_admin_cannot_update_is_active_to_false(
        self, client: TestClient
    ) -> None:
        """
        Using PUT /users/{id} with is_active=false on the last admin must also
        be rejected by the last-admin protection rule.
        """
        self._ensure_single_active_admin(client)
        admin_id = self._get_admin_id(client)

        resp = client.put(
            f"{USERS_URL}/{admin_id}",
            json={"is_active": False},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 400

        db_user = _get_user_from_db(admin_id)
        assert db_user.is_active is True
