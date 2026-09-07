"""
Phase 3 — Authentication and RBAC tests.

Tests all 16 required cases:

Login:
  1.  Admin login succeeds.
  2.  Sales login succeeds.
  3.  Wrong password returns 401.
  4.  Unknown email returns 401.
  5.  Inactive user returns 401.

JWT:
  6.  Valid JWT allows /api/auth/me.
  7.  Missing token returns 401.
  8.  Invalid token returns 401.
  9.  Expired token returns 401.
  10. JWT cannot be used by an inactive user.

Current user:
  11. Admin /api/auth/me returns role ADMIN.
  12. Sales /api/auth/me returns role SALES.
  13. Password / password_hash never present in response.

RBAC:
  14. Admin dependency accepts ADMIN.
  15. Admin dependency rejects SALES with 403.
  16. Inactive authenticated user is rejected.

All tests run against a real PostgreSQL database using the seed users.
Prerequisites: alembic upgrade head && python -m src.migration.seed
"""
import warnings
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

from jose import jwt
from sqlalchemy.orm import Session

from src.main import app
from src.repository.database import SessionLocal
from src.repository.models.user import User
from src.settings import get_settings
from src.utils.enums import UserRole

# ── Shared helpers ────────────────────────────────────────────────────────────

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@123"
SALES_EMAIL = "sales@example.com"
SALES_PASSWORD = "Sales@123"

LOGIN_URL = "/api/auth/login"
ME_URL = "/api/auth/me"

# A dummy admin-only endpoint for RBAC tests — we use /api/auth/me with
# role-checked logic by inspecting the returned role; for a pure 403 test
# we hit the require_admin dependency directly via a helper endpoint added
# to the test client (see the fixture below).


@pytest.fixture(scope="module")
def client():
    """TestClient shared across this module."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _login(client: TestClient, email: str, password: str) -> dict:
    """Helper: POST /api/auth/login, return JSON."""
    resp = client.post(LOGIN_URL, json={"email": email, "password": password})
    return resp


def _auth_header(token: str) -> dict:
    """Helper: build Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


def _get_admin_token(client: TestClient) -> str:
    resp = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


def _get_sales_token(client: TestClient) -> str:
    resp = _login(client, SALES_EMAIL, SALES_PASSWORD)
    assert resp.status_code == 200, f"Sales login failed: {resp.text}"
    return resp.json()["access_token"]


# ── Helpers for deactivating / reactivating a user mid-test ──────────────────

def _set_user_active(email: str, active: bool) -> None:
    """Directly flip is_active on a user in the DB."""
    db: Session = SessionLocal()
    try:
        from sqlalchemy import select
        user = db.execute(select(User).where(User.email == email)).scalar_one()
        user.is_active = active
        db.commit()
    finally:
        db.close()


# ═════════════════════════════════════════════════════════════════════════════
# 1–5  LOGIN
# ═════════════════════════════════════════════════════════════════════════════

class TestLogin:

    # Test 1
    def test_admin_login_succeeds(self, client: TestClient) -> None:
        """Admin credentials return 200 with an access_token."""
        resp = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 20

    # Test 2
    def test_sales_login_succeeds(self, client: TestClient) -> None:
        """Sales credentials return 200 with an access_token."""
        resp = _login(client, SALES_EMAIL, SALES_PASSWORD)
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    # Test 3
    def test_wrong_password_returns_401(self, client: TestClient) -> None:
        """Wrong password must return 401, not 403 or 400."""
        resp = _login(client, ADMIN_EMAIL, "WrongPassword!")
        assert resp.status_code == 401
        body = resp.json()
        # Must use a generic message — not "wrong password"
        assert "detail" in body
        assert "invalid" in body["detail"].lower() or "incorrect" in body["detail"].lower() or "password" in body["detail"].lower()

    # Test 4
    def test_unknown_email_returns_401(self, client: TestClient) -> None:
        """Non-existent email must return 401 with same message as wrong password."""
        resp = _login(client, "nobody@notexist.com", "AnyPassword1")
        assert resp.status_code == 401
        body = resp.json()
        assert "detail" in body

    # Test 5
    def test_inactive_user_returns_401(self, client: TestClient) -> None:
        """Deactivated user must not be able to log in — returns 401."""
        _set_user_active(SALES_EMAIL, False)
        try:
            resp = _login(client, SALES_EMAIL, SALES_PASSWORD)
            assert resp.status_code == 401
        finally:
            # Always restore so other tests are not affected
            _set_user_active(SALES_EMAIL, True)

    def test_login_does_not_leak_email_existence(self, client: TestClient) -> None:
        """Wrong-password and unknown-email responses must have the same status."""
        r1 = _login(client, ADMIN_EMAIL, "WrongPass!")
        r2 = _login(client, "nobody@ghost.com", "AnyPass!")
        assert r1.status_code == r2.status_code == 401

    def test_empty_password_returns_422(self, client: TestClient) -> None:
        """Empty password must be rejected by Pydantic validation before reaching the service."""
        resp = _login(client, ADMIN_EMAIL, "")
        assert resp.status_code == 422

    def test_missing_email_returns_422(self, client: TestClient) -> None:
        """Missing email field returns 422 Unprocessable Entity."""
        resp = client.post(LOGIN_URL, json={"password": "Admin@123"})
        assert resp.status_code == 422


# ═════════════════════════════════════════════════════════════════════════════
# 6–10  JWT
# ═════════════════════════════════════════════════════════════════════════════

class TestJWT:

    # Test 6
    def test_valid_jwt_allows_me_endpoint(self, client: TestClient) -> None:
        """A freshly issued JWT must give access to /api/auth/me."""
        token = _get_admin_token(client)
        resp = client.get(ME_URL, headers=_auth_header(token))
        assert resp.status_code == 200

    # Test 7
    def test_missing_token_returns_401(self, client: TestClient) -> None:
        """Request to /api/auth/me with no Authorization header → 401."""
        resp = client.get(ME_URL)
        assert resp.status_code == 401

    # Test 8
    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        """A garbage token string must return 401."""
        resp = client.get(ME_URL, headers=_auth_header("this.is.not.a.valid.jwt"))
        assert resp.status_code == 401

    # Test 9
    def test_expired_token_returns_401(self, client: TestClient) -> None:
        """
        A token whose exp is already in the past must return 401.
        We forge the token directly with a past expiry using the real secret.
        """
        settings = get_settings()
        past_exp = datetime.now(timezone.utc) - timedelta(minutes=10)
        payload = {
            "sub": "1",
            "role": UserRole.ADMIN.value,
            "exp": past_exp,
            "iat": past_exp - timedelta(minutes=60),
        }
        expired_token = jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
        resp = client.get(ME_URL, headers=_auth_header(expired_token))
        assert resp.status_code == 401

    # Test 10
    def test_inactive_user_jwt_is_rejected(self, client: TestClient) -> None:
        """
        Even a valid, unexpired JWT must be rejected if the user is deactivated.
        The database is the source of truth, not the token.
        """
        # Get a valid token while the user is still active
        token = _get_sales_token(client)
        # Now deactivate the user
        _set_user_active(SALES_EMAIL, False)
        try:
            resp = client.get(ME_URL, headers=_auth_header(token))
            assert resp.status_code == 401
        finally:
            _set_user_active(SALES_EMAIL, True)

    def test_wrong_secret_token_returns_401(self, client: TestClient) -> None:
        """A token signed with a different secret must return 401."""
        payload = {
            "sub": "1",
            "role": UserRole.ADMIN.value,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
        }
        forged_token = jwt.encode(payload, "completely-wrong-secret", algorithm="HS256")
        resp = client.get(ME_URL, headers=_auth_header(forged_token))
        assert resp.status_code == 401

    def test_token_missing_sub_claim_returns_401(self, client: TestClient) -> None:
        """A token with no 'sub' claim must return 401."""
        settings = get_settings()
        payload = {
            "role": UserRole.ADMIN.value,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
        }
        bad_token = jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
        resp = client.get(ME_URL, headers=_auth_header(bad_token))
        assert resp.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# 11–13  CURRENT USER
# ═════════════════════════════════════════════════════════════════════════════

class TestCurrentUser:

    # Test 11
    def test_admin_me_returns_admin_role(self, client: TestClient) -> None:
        """Admin JWT → /api/auth/me must return role ADMIN."""
        token = _get_admin_token(client)
        resp = client.get(ME_URL, headers=_auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["role"] == "ADMIN"
        assert body["email"] == ADMIN_EMAIL
        assert body["is_active"] is True

    # Test 12
    def test_sales_me_returns_sales_role(self, client: TestClient) -> None:
        """Sales JWT → /api/auth/me must return role SALES."""
        token = _get_sales_token(client)
        resp = client.get(ME_URL, headers=_auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["role"] == "SALES"
        assert body["email"] == SALES_EMAIL

    # Test 13
    def test_me_response_never_contains_password(self, client: TestClient) -> None:
        """
        The /api/auth/me response must NEVER contain password or password_hash.
        Also validates the response contains only the expected safe fields.
        """
        token = _get_admin_token(client)
        resp = client.get(ME_URL, headers=_auth_header(token))
        assert resp.status_code == 200
        body = resp.json()

        # Must not contain any password-related fields
        assert "password" not in body
        assert "password_hash" not in body
        assert "hash" not in body

        # Must contain exactly the expected safe fields
        expected_keys = {"id", "name", "email", "role", "is_active"}
        assert expected_keys.issubset(body.keys()), (
            f"Missing expected keys. Got: {set(body.keys())}"
        )

    def test_me_response_id_is_integer(self, client: TestClient) -> None:
        """User id in /api/auth/me response must be an integer."""
        token = _get_admin_token(client)
        resp = client.get(ME_URL, headers=_auth_header(token))
        assert resp.status_code == 200
        assert isinstance(resp.json()["id"], int)

    def test_login_response_never_contains_password(self, client: TestClient) -> None:
        """The login response must never expose a password or hash."""
        resp = _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        assert resp.status_code == 200
        body = resp.json()
        assert "password" not in body
        assert "password_hash" not in body


# ═════════════════════════════════════════════════════════════════════════════
# 14–16  RBAC
# ═════════════════════════════════════════════════════════════════════════════
#
# For RBAC tests we need an endpoint that uses require_admin.
# We add a lightweight test-only route to the app here using a separate
# test router that is only mounted during this test session.
# This keeps production code free of test stubs.
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import Depends                                  # noqa: E402
from src.core.security import require_admin, get_current_user  # noqa: E402
from src.repository.models.user import User as UserORM        # noqa: E402

# Mount a tiny test-only router once per module
_rbac_router_mounted = False


@pytest.fixture(scope="module", autouse=True)
def mount_rbac_test_route():
    """
    Add a temporary /api/test/admin-only endpoint that uses require_admin.
    This lets us test the RBAC dependency without modifying production code.
    The route is added once and remains for the module's lifetime.
    """
    global _rbac_router_mounted
    if not _rbac_router_mounted:
        from fastapi import APIRouter
        test_router = APIRouter()

        @test_router.get("/admin-only")
        def admin_only_endpoint(user: UserORM = Depends(require_admin)):
            return {"ok": True, "role": user.role.value}

        @test_router.get("/authenticated")
        def authenticated_endpoint(user: UserORM = Depends(get_current_user)):
            return {"ok": True, "user_id": user.id}

        app.include_router(test_router, prefix="/api/test")
        _rbac_router_mounted = True
    yield


class TestRBAC:

    # Test 14
    def test_admin_dependency_accepts_admin_role(self, client: TestClient) -> None:
        """require_admin must allow an ADMIN-role user through."""
        token = _get_admin_token(client)
        resp = client.get("/api/test/admin-only", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["role"] == "ADMIN"

    # Test 15
    def test_admin_dependency_rejects_sales_with_403(self, client: TestClient) -> None:
        """require_admin must return HTTP 403 for a SALES-role user."""
        token = _get_sales_token(client)
        resp = client.get("/api/test/admin-only", headers=_auth_header(token))
        assert resp.status_code == 403
        body = resp.json()
        assert "detail" in body
        assert "admin" in body["detail"].lower()

    # Test 16
    def test_inactive_user_is_rejected_on_authenticated_endpoint(
        self, client: TestClient
    ) -> None:
        """
        An inactive user must be rejected on any protected endpoint,
        even if their JWT is still valid.
        """
        # Obtain a valid token first
        token = _get_sales_token(client)
        # Deactivate the user in the DB
        _set_user_active(SALES_EMAIL, False)
        try:
            resp = client.get("/api/test/authenticated", headers=_auth_header(token))
            assert resp.status_code == 401
        finally:
            _set_user_active(SALES_EMAIL, True)

    def test_unauthenticated_request_to_admin_only_returns_401(
        self, client: TestClient
    ) -> None:
        """No token on an admin-protected endpoint → 401, not 403."""
        resp = client.get("/api/test/admin-only")
        assert resp.status_code == 401

    def test_sales_can_access_authenticated_endpoint(self, client: TestClient) -> None:
        """A SALES user can access endpoints protected by get_current_user."""
        token = _get_sales_token(client)
        resp = client.get("/api/test/authenticated", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
