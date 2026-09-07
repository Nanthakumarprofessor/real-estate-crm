"""
Phase 5 — Lead Management API tests.

Covers:
  Authorization
  Lead CRUD (admin + sales, ownership, soft-delete)
  Search / filter / pagination
  Lead Notes (create, list, delete, ownership)
  Follow-ups (create, list, update, past-date rejection, status filter)
  Regression — existing Phase 1-4 tests must remain green

All tests use isolated data created within the test. DB helpers clean up
created leads/notes/follow-ups to keep the database state predictable.
"""
import uuid
import warnings
from datetime import datetime, timedelta, timezone

warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.main import app
from src.repository.database import SessionLocal
from src.repository.models.lead import Lead
from src.repository.models.lead_note import LeadNote
from src.repository.models.follow_up import FollowUp
from src.repository.models.user import User
from src.utils.enums import LeadStage, LeadSource, UserRole, FollowUpStatus

# ── URLs ──────────────────────────────────────────────────────────────────────
LEADS_URL = "/api/leads"
FOLLOW_UPS_URL = "/api/follow-ups"
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


# ── Auth helpers ──────────────────────────────────────────────────────────────
def _get_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post(LOGIN_URL, json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


def _admin_headers(client: TestClient) -> dict:
    return {"Authorization": f"Bearer {_get_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)}"}


def _sales_headers(client: TestClient) -> dict:
    return {"Authorization": f"Bearer {_get_token(client, SALES_EMAIL, SALES_PASSWORD)}"}


# ── DB helpers ────────────────────────────────────────────────────────────────
def _get_db() -> Session:
    return SessionLocal()


def _get_sales_user_id() -> int:
    db = _get_db()
    try:
        user = db.execute(select(User).where(User.email == SALES_EMAIL)).scalar_one()
        return user.id
    finally:
        db.close()


def _get_admin_user_id() -> int:
    db = _get_db()
    try:
        user = db.execute(select(User).where(User.email == ADMIN_EMAIL)).scalar_one()
        return user.id
    finally:
        db.close()


def _create_sales_user(client: TestClient) -> dict:
    """Create a second Sales user for isolation tests. Returns the user dict."""
    email = f"sales2_{uuid.uuid4().hex[:8]}@test.com"
    resp = client.post(
        "/api/users",
        json={"name": "Sales Two", "email": email, "password": "Test@1234", "role": "SALES"},
        headers=_admin_headers(client),
    )
    assert resp.status_code == 201
    return resp.json()


def _login_as(client: TestClient, email: str, password: str = "Test@1234") -> dict:
    return {"Authorization": f"Bearer {_get_token(client, email, password)}"}


def _delete_lead(lead_id: int) -> None:
    db = _get_db()
    try:
        lead = db.execute(select(Lead).where(Lead.id == lead_id)).scalar_one_or_none()
        if lead:
            db.delete(lead)
            db.commit()
    finally:
        db.close()


def _delete_user(user_id: int) -> None:
    db = _get_db()
    try:
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()


def _future_dt(hours: int = 24) -> str:
    """ISO-8601 datetime string that is `hours` hours from now (UTC)."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past_dt(hours: int = 1) -> str:
    """ISO-8601 datetime string that is `hours` hours in the past (UTC)."""
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


# ── Payload helpers ───────────────────────────────────────────────────────────
def _lead_payload(**overrides) -> dict:
    defaults = {
        "name": f"Test Lead {uuid.uuid4().hex[:6]}",
        "email": f"lead_{uuid.uuid4().hex[:8]}@test.com",
        "phone": "9000000000",
        "source": "WEBSITE",
        "stage": "NEW",
    }
    defaults.update(overrides)
    return defaults


# ═════════════════════════════════════════════════════════════════════════════
# AUTHORIZATION — Unauthenticated access
# ═════════════════════════════════════════════════════════════════════════════

class TestLeadAuthorization:

    def test_unauthenticated_cannot_list_leads(self, client: TestClient) -> None:
        resp = client.get(LEADS_URL)
        assert resp.status_code == 401

    def test_unauthenticated_cannot_create_lead(self, client: TestClient) -> None:
        resp = client.post(LEADS_URL, json=_lead_payload())
        assert resp.status_code == 401

    def test_unauthenticated_cannot_get_lead(self, client: TestClient) -> None:
        resp = client.get(f"{LEADS_URL}/1")
        assert resp.status_code == 401

    def test_unauthenticated_cannot_delete_lead(self, client: TestClient) -> None:
        resp = client.delete(f"{LEADS_URL}/1")
        assert resp.status_code == 401

    def test_sales_cannot_delete_lead(self, client: TestClient) -> None:
        # Create a lead as admin, then try to delete as sales
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_admin_headers(client))
        assert resp.status_code == 201
        lead_id = resp.json()["id"]
        try:
            del_resp = client.delete(f"{LEADS_URL}/{lead_id}", headers=_sales_headers(client))
            assert del_resp.status_code == 403
        finally:
            _delete_lead(lead_id)

    def test_unauthenticated_cannot_list_follow_ups(self, client: TestClient) -> None:
        resp = client.get(FOLLOW_UPS_URL)
        assert resp.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# LEAD CRUD — Admin
# ═════════════════════════════════════════════════════════════════════════════

class TestAdminLeadCRUD:

    def test_admin_can_create_lead(self, client: TestClient) -> None:
        payload = _lead_payload()
        resp = client.post(LEADS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == payload["name"]
        assert body["stage"] == "NEW"
        assert body["is_active"] is True
        _delete_lead(body["id"])

    def test_admin_create_lead_with_assignment(self, client: TestClient) -> None:
        sales_id = _get_sales_user_id()
        payload = _lead_payload(assigned_to=sales_id)
        resp = client.post(LEADS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 201
        body = resp.json()
        assert body["assigned_to"] == sales_id
        _delete_lead(body["id"])

    def test_admin_create_lead_invalid_assignee_returns_400(self, client: TestClient) -> None:
        payload = _lead_payload(assigned_to=999999)
        resp = client.post(LEADS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 400

    def test_admin_can_get_any_lead(self, client: TestClient) -> None:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_admin_headers(client))
        assert resp.status_code == 201
        lead_id = resp.json()["id"]
        try:
            get_resp = client.get(f"{LEADS_URL}/{lead_id}", headers=_admin_headers(client))
            assert get_resp.status_code == 200
            assert get_resp.json()["id"] == lead_id
        finally:
            _delete_lead(lead_id)

    def test_admin_can_update_any_lead(self, client: TestClient) -> None:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_admin_headers(client))
        lead_id = resp.json()["id"]
        try:
            upd = client.put(
                f"{LEADS_URL}/{lead_id}",
                json={"name": "Updated Name", "stage": "CONTACTED"},
                headers=_admin_headers(client),
            )
            assert upd.status_code == 200
            body = upd.json()
            assert body["name"] == "Updated Name"
            assert body["stage"] == "CONTACTED"
        finally:
            _delete_lead(lead_id)

    def test_admin_can_assign_lead(self, client: TestClient) -> None:
        sales_id = _get_sales_user_id()
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_admin_headers(client))
        lead_id = resp.json()["id"]
        try:
            upd = client.put(
                f"{LEADS_URL}/{lead_id}",
                json={"assigned_to": sales_id},
                headers=_admin_headers(client),
            )
            assert upd.status_code == 200
            assert upd.json()["assigned_to"] == sales_id
        finally:
            _delete_lead(lead_id)

    def test_admin_can_soft_delete_lead(self, client: TestClient) -> None:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_admin_headers(client))
        lead_id = resp.json()["id"]
        try:
            del_resp = client.delete(f"{LEADS_URL}/{lead_id}", headers=_admin_headers(client))
            assert del_resp.status_code == 200
            assert del_resp.json()["is_active"] is False
            # Lead still exists in DB
            db = _get_db()
            try:
                lead = db.execute(select(Lead).where(Lead.id == lead_id)).scalar_one_or_none()
                assert lead is not None
                assert lead.is_active is False
            finally:
                db.close()
        finally:
            _delete_lead(lead_id)

    def test_soft_delete_is_idempotent(self, client: TestClient) -> None:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_admin_headers(client))
        lead_id = resp.json()["id"]
        try:
            client.delete(f"{LEADS_URL}/{lead_id}", headers=_admin_headers(client))
            # Delete again — should return 200 with is_active=False
            del2 = client.delete(f"{LEADS_URL}/{lead_id}", headers=_admin_headers(client))
            assert del2.status_code == 200
            assert del2.json()["is_active"] is False
        finally:
            _delete_lead(lead_id)

    def test_get_nonexistent_lead_returns_404(self, client: TestClient) -> None:
        resp = client.get(f"{LEADS_URL}/999999", headers=_admin_headers(client))
        assert resp.status_code == 404

    def test_update_nonexistent_lead_returns_404(self, client: TestClient) -> None:
        resp = client.put(
            f"{LEADS_URL}/999999",
            json={"name": "Nobody"},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 404

    def test_lead_missing_name_returns_422(self, client: TestClient) -> None:
        payload = {"email": "noname@test.com"}
        resp = client.post(LEADS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 422

    def test_lead_empty_name_returns_422(self, client: TestClient) -> None:
        payload = _lead_payload(name="   ")
        resp = client.post(LEADS_URL, json=payload, headers=_admin_headers(client))
        assert resp.status_code == 422


# ═════════════════════════════════════════════════════════════════════════════
# LEAD CRUD — Sales
# ═════════════════════════════════════════════════════════════════════════════

class TestSalesLeadCRUD:

    def test_sales_can_create_lead(self, client: TestClient) -> None:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_sales_headers(client))
        assert resp.status_code == 201
        body = resp.json()
        sales_id = _get_sales_user_id()
        # Sales lead must be assigned to themselves
        assert body["assigned_to"] == sales_id
        _delete_lead(body["id"])

    def test_sales_assigned_to_ignored_on_create(self, client: TestClient) -> None:
        """Sales cannot self-assign to another user — assigned_to is forced to themselves."""
        admin_id = _get_admin_user_id()
        payload = _lead_payload(assigned_to=admin_id)
        resp = client.post(LEADS_URL, json=payload, headers=_sales_headers(client))
        assert resp.status_code == 201
        sales_id = _get_sales_user_id()
        assert resp.json()["assigned_to"] == sales_id
        _delete_lead(resp.json()["id"])

    def test_sales_can_get_own_lead(self, client: TestClient) -> None:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_sales_headers(client))
        lead_id = resp.json()["id"]
        try:
            get_resp = client.get(f"{LEADS_URL}/{lead_id}", headers=_sales_headers(client))
            assert get_resp.status_code == 200
        finally:
            _delete_lead(lead_id)

    def test_sales_cannot_get_another_users_lead(self, client: TestClient) -> None:
        # Create a second sales user and their lead
        sales2 = _create_sales_user(client)
        sales2_headers = _login_as(client, sales2["email"])
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=sales2_headers)
        lead_id = resp.json()["id"]
        try:
            # Primary sales user tries to access it
            get_resp = client.get(f"{LEADS_URL}/{lead_id}", headers=_sales_headers(client))
            assert get_resp.status_code == 403
        finally:
            _delete_lead(lead_id)
            _delete_user(sales2["id"])

    def test_sales_can_update_own_lead(self, client: TestClient) -> None:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_sales_headers(client))
        lead_id = resp.json()["id"]
        try:
            upd = client.put(
                f"{LEADS_URL}/{lead_id}",
                json={"stage": "CONTACTED"},
                headers=_sales_headers(client),
            )
            assert upd.status_code == 200
            assert upd.json()["stage"] == "CONTACTED"
        finally:
            _delete_lead(lead_id)

    def test_sales_cannot_update_another_users_lead(self, client: TestClient) -> None:
        sales2 = _create_sales_user(client)
        sales2_headers = _login_as(client, sales2["email"])
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=sales2_headers)
        lead_id = resp.json()["id"]
        try:
            upd = client.put(
                f"{LEADS_URL}/{lead_id}",
                json={"stage": "CONTACTED"},
                headers=_sales_headers(client),
            )
            assert upd.status_code == 403
        finally:
            _delete_lead(lead_id)
            _delete_user(sales2["id"])

    def test_sales_cannot_reassign_lead(self, client: TestClient) -> None:
        """Sales update with assigned_to field is silently ignored — assignment unchanged."""
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_sales_headers(client))
        lead_id = resp.json()["id"]
        admin_id = _get_admin_user_id()
        sales_id = _get_sales_user_id()
        try:
            upd = client.put(
                f"{LEADS_URL}/{lead_id}",
                json={"assigned_to": admin_id},
                headers=_sales_headers(client),
            )
            assert upd.status_code == 200
            # assignment must not have changed
            assert upd.json()["assigned_to"] == sales_id
        finally:
            _delete_lead(lead_id)


# ═════════════════════════════════════════════════════════════════════════════
# LEAD LISTING — Search / Filter / Pagination
# ═════════════════════════════════════════════════════════════════════════════

class TestLeadListing:

    def test_list_response_shape(self, client: TestClient) -> None:
        resp = client.get(LEADS_URL, headers=_admin_headers(client))
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "size" in body

    def test_pagination(self, client: TestClient) -> None:
        resp = client.get(f"{LEADS_URL}?page=1&size=2", headers=_admin_headers(client))
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 2
        assert body["page"] == 1
        assert body["size"] == 2

    def test_search_by_name(self, client: TestClient) -> None:
        unique = uuid.uuid4().hex[:8]
        payload = _lead_payload(name=f"UniqueNameSearch_{unique}")
        resp = client.post(LEADS_URL, json=payload, headers=_admin_headers(client))
        lead_id = resp.json()["id"]
        try:
            search = client.get(
                f"{LEADS_URL}?search={unique}",
                headers=_admin_headers(client),
            )
            assert search.status_code == 200
            names = [i["name"] for i in search.json()["items"]]
            assert any(unique in n for n in names)
        finally:
            _delete_lead(lead_id)

    def test_search_by_email(self, client: TestClient) -> None:
        unique = uuid.uuid4().hex[:8]
        payload = _lead_payload(email=f"unique_{unique}@searchtest.com")
        resp = client.post(LEADS_URL, json=payload, headers=_admin_headers(client))
        lead_id = resp.json()["id"]
        try:
            search = client.get(
                f"{LEADS_URL}?search={unique}",
                headers=_admin_headers(client),
            )
            assert search.status_code == 200
            emails = [i["email"] for i in search.json()["items"]]
            assert any(unique in (e or "") for e in emails)
        finally:
            _delete_lead(lead_id)

    def test_stage_filter(self, client: TestClient) -> None:
        payload = _lead_payload(stage="NEGOTIATION")
        resp = client.post(LEADS_URL, json=payload, headers=_admin_headers(client))
        lead_id = resp.json()["id"]
        try:
            filtered = client.get(
                f"{LEADS_URL}?stage=NEGOTIATION",
                headers=_admin_headers(client),
            )
            assert filtered.status_code == 200
            stages = [i["stage"] for i in filtered.json()["items"]]
            assert all(s == "NEGOTIATION" for s in stages)
            assert "NEGOTIATION" in stages
        finally:
            _delete_lead(lead_id)

    def test_assigned_to_filter_admin(self, client: TestClient) -> None:
        sales_id = _get_sales_user_id()
        resp = client.post(
            LEADS_URL,
            json=_lead_payload(assigned_to=sales_id),
            headers=_admin_headers(client),
        )
        lead_id = resp.json()["id"]
        try:
            filtered = client.get(
                f"{LEADS_URL}?assigned_to={sales_id}",
                headers=_admin_headers(client),
            )
            assert filtered.status_code == 200
            items = filtered.json()["items"]
            assert all(i["assigned_to"] == sales_id for i in items)
        finally:
            _delete_lead(lead_id)

    def test_inactive_leads_excluded_by_default(self, client: TestClient) -> None:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_admin_headers(client))
        lead_id = resp.json()["id"]
        try:
            client.delete(f"{LEADS_URL}/{lead_id}", headers=_admin_headers(client))
            # Default listing should not include it
            listing = client.get(LEADS_URL, headers=_admin_headers(client))
            ids = [i["id"] for i in listing.json()["items"]]
            assert lead_id not in ids
        finally:
            _delete_lead(lead_id)

    def test_is_active_false_filter_shows_inactive(self, client: TestClient) -> None:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_admin_headers(client))
        lead_id = resp.json()["id"]
        try:
            client.delete(f"{LEADS_URL}/{lead_id}", headers=_admin_headers(client))
            listing = client.get(
                f"{LEADS_URL}?is_active=false",
                headers=_admin_headers(client),
            )
            ids = [i["id"] for i in listing.json()["items"]]
            assert lead_id in ids
        finally:
            _delete_lead(lead_id)

    def test_sales_only_sees_own_leads(self, client: TestClient) -> None:
        # Create a lead assigned to admin (not visible to sales)
        admin_id = _get_admin_user_id()
        resp = client.post(
            LEADS_URL,
            json=_lead_payload(assigned_to=admin_id),
            headers=_admin_headers(client),
        )
        admin_lead_id = resp.json()["id"]
        try:
            listing = client.get(LEADS_URL, headers=_sales_headers(client))
            assert listing.status_code == 200
            items = listing.json()["items"]
            sales_id = _get_sales_user_id()
            # All returned items must be assigned to sales user
            for item in items:
                assert item["assigned_to"] == sales_id
        finally:
            _delete_lead(admin_lead_id)


# ═════════════════════════════════════════════════════════════════════════════
# LEAD NOTES
# ═════════════════════════════════════════════════════════════════════════════

class TestLeadNotes:

    def _make_lead_for_sales(self, client: TestClient) -> int:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_sales_headers(client))
        assert resp.status_code == 201
        return resp.json()["id"]

    def _make_lead_for_admin(self, client: TestClient) -> int:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_admin_headers(client))
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_admin_can_add_note_to_any_lead(self, client: TestClient) -> None:
        lead_id = self._make_lead_for_admin(client)
        try:
            resp = client.post(
                f"{LEADS_URL}/{lead_id}/notes",
                json={"note": "Admin note text"},
                headers=_admin_headers(client),
            )
            assert resp.status_code == 201
            body = resp.json()
            assert body["note"] == "Admin note text"
            assert body["lead_id"] == lead_id
        finally:
            _delete_lead(lead_id)

    def test_sales_can_add_note_to_own_lead(self, client: TestClient) -> None:
        lead_id = self._make_lead_for_sales(client)
        try:
            resp = client.post(
                f"{LEADS_URL}/{lead_id}/notes",
                json={"note": "Sales note"},
                headers=_sales_headers(client),
            )
            assert resp.status_code == 201
            assert resp.json()["note"] == "Sales note"
        finally:
            _delete_lead(lead_id)

    def test_sales_cannot_add_note_to_another_users_lead(self, client: TestClient) -> None:
        sales2 = _create_sales_user(client)
        sales2_headers = _login_as(client, sales2["email"])
        lead_id_for_s2 = client.post(LEADS_URL, json=_lead_payload(), headers=sales2_headers).json()["id"]
        try:
            resp = client.post(
                f"{LEADS_URL}/{lead_id_for_s2}/notes",
                json={"note": "Unauthorized note"},
                headers=_sales_headers(client),
            )
            assert resp.status_code == 403
        finally:
            _delete_lead(lead_id_for_s2)
            _delete_user(sales2["id"])

    def test_admin_can_list_notes_for_any_lead(self, client: TestClient) -> None:
        lead_id = self._make_lead_for_admin(client)
        try:
            client.post(
                f"{LEADS_URL}/{lead_id}/notes",
                json={"note": "Note 1"},
                headers=_admin_headers(client),
            )
            resp = client.get(f"{LEADS_URL}/{lead_id}/notes", headers=_admin_headers(client))
            assert resp.status_code == 200
            body = resp.json()
            assert "items" in body
            assert "total" in body
            assert body["total"] >= 1
        finally:
            _delete_lead(lead_id)

    def test_sales_can_list_notes_for_own_lead(self, client: TestClient) -> None:
        lead_id = self._make_lead_for_sales(client)
        try:
            resp = client.get(f"{LEADS_URL}/{lead_id}/notes", headers=_sales_headers(client))
            assert resp.status_code == 200
        finally:
            _delete_lead(lead_id)

    def test_sales_cannot_list_notes_for_another_users_lead(self, client: TestClient) -> None:
        sales2 = _create_sales_user(client)
        sales2_headers = _login_as(client, sales2["email"])
        lead_id = client.post(LEADS_URL, json=_lead_payload(), headers=sales2_headers).json()["id"]
        try:
            resp = client.get(f"{LEADS_URL}/{lead_id}/notes", headers=_sales_headers(client))
            assert resp.status_code == 403
        finally:
            _delete_lead(lead_id)
            _delete_user(sales2["id"])

    def test_notes_cannot_be_edited(self, client: TestClient) -> None:
        """There is no PUT/PATCH endpoint for notes — only POST and DELETE."""
        lead_id = self._make_lead_for_admin(client)
        try:
            note_resp = client.post(
                f"{LEADS_URL}/{lead_id}/notes",
                json={"note": "Original"},
                headers=_admin_headers(client),
            )
            note_id = note_resp.json()["id"]
            # PATCH/PUT on this endpoint should return 405
            patch = client.patch(
                f"{LEADS_URL}/{lead_id}/notes/{note_id}",
                json={"note": "Edited"},
                headers=_admin_headers(client),
            )
            assert patch.status_code == 405
        finally:
            _delete_lead(lead_id)

    def test_sales_can_delete_own_note(self, client: TestClient) -> None:
        lead_id = self._make_lead_for_sales(client)
        try:
            note_resp = client.post(
                f"{LEADS_URL}/{lead_id}/notes",
                json={"note": "My note"},
                headers=_sales_headers(client),
            )
            note_id = note_resp.json()["id"]
            del_resp = client.delete(
                f"{LEADS_URL}/{lead_id}/notes/{note_id}",
                headers=_sales_headers(client),
            )
            assert del_resp.status_code == 200
            assert "deleted" in del_resp.json()["message"].lower()
        finally:
            _delete_lead(lead_id)

    def test_sales_cannot_delete_another_users_note(self, client: TestClient) -> None:
        # Admin adds a note to a lead; sales tries to delete it
        sales_id = _get_sales_user_id()
        lead_resp = client.post(
            LEADS_URL,
            json=_lead_payload(assigned_to=sales_id),
            headers=_admin_headers(client),
        )
        lead_id = lead_resp.json()["id"]
        try:
            note_resp = client.post(
                f"{LEADS_URL}/{lead_id}/notes",
                json={"note": "Admin note"},
                headers=_admin_headers(client),
            )
            note_id = note_resp.json()["id"]
            del_resp = client.delete(
                f"{LEADS_URL}/{lead_id}/notes/{note_id}",
                headers=_sales_headers(client),
            )
            assert del_resp.status_code == 403
        finally:
            _delete_lead(lead_id)

    def test_admin_can_delete_any_note(self, client: TestClient) -> None:
        lead_id = self._make_lead_for_sales(client)
        try:
            note_resp = client.post(
                f"{LEADS_URL}/{lead_id}/notes",
                json={"note": "Sales note to delete"},
                headers=_sales_headers(client),
            )
            note_id = note_resp.json()["id"]
            del_resp = client.delete(
                f"{LEADS_URL}/{lead_id}/notes/{note_id}",
                headers=_admin_headers(client),
            )
            assert del_resp.status_code == 200
        finally:
            _delete_lead(lead_id)

    def test_delete_nonexistent_note_returns_404(self, client: TestClient) -> None:
        lead_id = self._make_lead_for_admin(client)
        try:
            resp = client.delete(
                f"{LEADS_URL}/{lead_id}/notes/999999",
                headers=_admin_headers(client),
            )
            assert resp.status_code == 404
        finally:
            _delete_lead(lead_id)

    def test_empty_note_returns_422(self, client: TestClient) -> None:
        lead_id = self._make_lead_for_admin(client)
        try:
            resp = client.post(
                f"{LEADS_URL}/{lead_id}/notes",
                json={"note": "   "},
                headers=_admin_headers(client),
            )
            assert resp.status_code == 422
        finally:
            _delete_lead(lead_id)

    def test_note_for_nonexistent_lead_returns_404(self, client: TestClient) -> None:
        resp = client.post(
            f"{LEADS_URL}/999999/notes",
            json={"note": "Ghost note"},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# FOLLOW-UPS
# ═════════════════════════════════════════════════════════════════════════════

class TestFollowUps:

    def _make_sales_lead(self, client: TestClient) -> int:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_sales_headers(client))
        assert resp.status_code == 201
        return resp.json()["id"]

    def _make_admin_lead(self, client: TestClient) -> int:
        resp = client.post(LEADS_URL, json=_lead_payload(), headers=_admin_headers(client))
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_admin_can_create_follow_up(self, client: TestClient) -> None:
        lead_id = self._make_admin_lead(client)
        try:
            resp = client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _future_dt(48)},
                headers=_admin_headers(client),
            )
            assert resp.status_code == 201
            body = resp.json()
            assert body["lead_id"] == lead_id
            assert body["status"] == "PENDING"
        finally:
            _delete_lead(lead_id)

    def test_sales_can_create_follow_up_for_own_lead(self, client: TestClient) -> None:
        lead_id = self._make_sales_lead(client)
        try:
            resp = client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _future_dt(24)},
                headers=_sales_headers(client),
            )
            assert resp.status_code == 201
        finally:
            _delete_lead(lead_id)

    def test_sales_cannot_create_follow_up_for_another_users_lead(self, client: TestClient) -> None:
        sales2 = _create_sales_user(client)
        sales2_headers = _login_as(client, sales2["email"])
        lead_id = client.post(LEADS_URL, json=_lead_payload(), headers=sales2_headers).json()["id"]
        try:
            resp = client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _future_dt(24)},
                headers=_sales_headers(client),
            )
            assert resp.status_code == 403
        finally:
            _delete_lead(lead_id)
            _delete_user(sales2["id"])

    def test_past_follow_up_date_rejected(self, client: TestClient) -> None:
        lead_id = self._make_admin_lead(client)
        try:
            resp = client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _past_dt(2)},
                headers=_admin_headers(client),
            )
            assert resp.status_code == 400
            assert resp.json()["error_code"] == "FOLLOW_UP_PAST_DATE"
        finally:
            _delete_lead(lead_id)

    def test_follow_up_for_nonexistent_lead_returns_404(self, client: TestClient) -> None:
        resp = client.post(
            f"{LEADS_URL}/999999/follow-ups",
            json={"follow_up_at": _future_dt(24)},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 404

    def test_list_follow_ups_for_lead(self, client: TestClient) -> None:
        lead_id = self._make_admin_lead(client)
        try:
            client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _future_dt(24)},
                headers=_admin_headers(client),
            )
            resp = client.get(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                headers=_admin_headers(client),
            )
            assert resp.status_code == 200
            body = resp.json()
            assert "items" in body
            assert body["total"] >= 1
        finally:
            _delete_lead(lead_id)

    def test_sales_cannot_list_follow_ups_for_another_users_lead(self, client: TestClient) -> None:
        sales2 = _create_sales_user(client)
        sales2_headers = _login_as(client, sales2["email"])
        lead_id = client.post(LEADS_URL, json=_lead_payload(), headers=sales2_headers).json()["id"]
        try:
            resp = client.get(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                headers=_sales_headers(client),
            )
            assert resp.status_code == 403
        finally:
            _delete_lead(lead_id)
            _delete_user(sales2["id"])

    def test_status_filter_on_lead_follow_ups(self, client: TestClient) -> None:
        lead_id = self._make_admin_lead(client)
        try:
            fu_resp = client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _future_dt(24), "status": "PENDING"},
                headers=_admin_headers(client),
            )
            assert fu_resp.status_code == 201
            pending = client.get(
                f"{LEADS_URL}/{lead_id}/follow-ups?status=PENDING",
                headers=_admin_headers(client),
            )
            assert pending.status_code == 200
            assert all(i["status"] == "PENDING" for i in pending.json()["items"])

            completed = client.get(
                f"{LEADS_URL}/{lead_id}/follow-ups?status=COMPLETED",
                headers=_admin_headers(client),
            )
            assert completed.status_code == 200
            assert all(i["status"] == "COMPLETED" for i in completed.json()["items"])
        finally:
            _delete_lead(lead_id)

    def test_update_follow_up_status(self, client: TestClient) -> None:
        lead_id = self._make_admin_lead(client)
        try:
            fu_resp = client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _future_dt(24)},
                headers=_admin_headers(client),
            )
            fu_id = fu_resp.json()["id"]
            upd = client.put(
                f"{FOLLOW_UPS_URL}/{fu_id}",
                json={"status": "COMPLETED"},
                headers=_admin_headers(client),
            )
            assert upd.status_code == 200
            assert upd.json()["status"] == "COMPLETED"
        finally:
            _delete_lead(lead_id)

    def test_update_follow_up_notes(self, client: TestClient) -> None:
        lead_id = self._make_admin_lead(client)
        try:
            fu_resp = client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _future_dt(24), "notes": "Original"},
                headers=_admin_headers(client),
            )
            fu_id = fu_resp.json()["id"]
            upd = client.put(
                f"{FOLLOW_UPS_URL}/{fu_id}",
                json={"notes": "Updated notes"},
                headers=_admin_headers(client),
            )
            assert upd.status_code == 200
            assert upd.json()["notes"] == "Updated notes"
        finally:
            _delete_lead(lead_id)

    def test_update_follow_up_past_date_rejected(self, client: TestClient) -> None:
        lead_id = self._make_admin_lead(client)
        try:
            fu_resp = client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _future_dt(24)},
                headers=_admin_headers(client),
            )
            fu_id = fu_resp.json()["id"]
            upd = client.put(
                f"{FOLLOW_UPS_URL}/{fu_id}",
                json={"follow_up_at": _past_dt(1)},
                headers=_admin_headers(client),
            )
            assert upd.status_code == 400
            assert upd.json()["error_code"] == "FOLLOW_UP_PAST_DATE"
        finally:
            _delete_lead(lead_id)

    def test_sales_cannot_update_follow_up_for_another_users_lead(self, client: TestClient) -> None:
        sales2 = _create_sales_user(client)
        sales2_headers = _login_as(client, sales2["email"])
        lead_id = client.post(LEADS_URL, json=_lead_payload(), headers=sales2_headers).json()["id"]
        try:
            fu_resp = client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _future_dt(24)},
                headers=sales2_headers,
            )
            fu_id = fu_resp.json()["id"]
            upd = client.put(
                f"{FOLLOW_UPS_URL}/{fu_id}",
                json={"status": "COMPLETED"},
                headers=_sales_headers(client),
            )
            assert upd.status_code == 403
        finally:
            _delete_lead(lead_id)
            _delete_user(sales2["id"])

    def test_update_nonexistent_follow_up_returns_404(self, client: TestClient) -> None:
        resp = client.put(
            f"{FOLLOW_UPS_URL}/999999",
            json={"status": "COMPLETED"},
            headers=_admin_headers(client),
        )
        assert resp.status_code == 404

    def test_global_follow_up_list_admin_sees_all(self, client: TestClient) -> None:
        lead_id = self._make_admin_lead(client)
        try:
            client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _future_dt(24)},
                headers=_admin_headers(client),
            )
            resp = client.get(FOLLOW_UPS_URL, headers=_admin_headers(client))
            assert resp.status_code == 200
            body = resp.json()
            assert "items" in body
            assert "total" in body
            assert body["total"] >= 1
        finally:
            _delete_lead(lead_id)

    def test_global_follow_up_list_sales_scoped(self, client: TestClient) -> None:
        # Admin lead (not assigned to sales) — sales should not see its follow-ups
        lead_id = self._make_admin_lead(client)
        try:
            fu_resp = client.post(
                f"{LEADS_URL}/{lead_id}/follow-ups",
                json={"follow_up_at": _future_dt(48)},
                headers=_admin_headers(client),
            )
            fu_id = fu_resp.json()["id"]
            resp = client.get(FOLLOW_UPS_URL, headers=_sales_headers(client))
            assert resp.status_code == 200
            fu_ids = [i["id"] for i in resp.json()["items"]]
            assert fu_id not in fu_ids
        finally:
            _delete_lead(lead_id)

    def test_global_follow_up_status_filter(self, client: TestClient) -> None:
        resp = client.get(
            f"{FOLLOW_UPS_URL}?status=PENDING",
            headers=_admin_headers(client),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["status"] == "PENDING" for i in items)

    def test_global_follow_up_list_pagination(self, client: TestClient) -> None:
        resp = client.get(
            f"{FOLLOW_UPS_URL}?page=1&size=2",
            headers=_admin_headers(client),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 2
        assert body["page"] == 1
        assert body["size"] == 2
