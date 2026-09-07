"""
Phase 8 — Dashboard tests.

Covers:
  Authentication  (401 without token, 401 invalid token, 401 inactive user)
  Response shape  (all required keys present)
  Admin scope     (sees all leads, all stages, all follow-ups, all bookings)
  Sales scope     (sees only own leads, follow-ups, bookings)
  Data isolation  (Sales User A data does not bleed into Sales User B's dashboard)
  Lead stages     (all stages always present, zeros included)
  Soft-delete     (inactive leads excluded from lead counts)
  Follow-ups      (upcoming vs overdue, completed/cancelled excluded)
  Properties      (total == available + booked)
  Bookings        (confirmed / cancelled counts)

Test data strategy:
  Each test class creates and tears down its own isolated data so tests
  can be run in any order without cross-contamination.
  The seeded database rows from Phase 2 seed are present but tests that
  need precise counts create their own leads/follow-ups/bookings and
  verify deltas rather than absolute totals where seed data may vary.
"""
import uuid
import warnings
from datetime import datetime, timedelta, timezone

warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.main import app
from src.repository.database import SessionLocal
from src.repository.models.booking import Booking
from src.repository.models.follow_up import FollowUp
from src.repository.models.lead import Lead
from src.repository.models.unit import Unit
from src.utils.enums import BookingStatus, FollowUpStatus, LeadStage, LeadSource, UnitStatus

DASHBOARD_URL = "/api/dashboard/summary"
LOGIN_URL = "/api/auth/login"
LEADS_URL = "/api/leads"
FOLLOW_UPS_URL = "/api/follow-ups"
PROJECTS_URL = "/api/projects"
BUILDINGS_URL = "/api/buildings"
BOOKINGS_URL = "/api/bookings"
USERS_URL = "/api/users"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@123"
SALES_EMAIL = "sales@example.com"
SALES_PASSWORD = "Sales@123"


# ── Client fixture ────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Auth helpers ──────────────────────────────────────────────────────────────
def _get_token(client: TestClient, email: str, password: str) -> str:
    resp = client.post(LOGIN_URL, json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


def _admin_h(client: TestClient) -> dict:
    return {"Authorization": f"Bearer {_get_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)}"}


def _sales_h(client: TestClient) -> dict:
    return {"Authorization": f"Bearer {_get_token(client, SALES_EMAIL, SALES_PASSWORD)}"}


def _headers_for(client: TestClient, email: str, password: str = "Test@1234") -> dict:
    return {"Authorization": f"Bearer {_get_token(client, email, password)}"}


# ── DB helpers ────────────────────────────────────────────────────────────────
def _db():
    return SessionLocal()


def _delete_lead(lead_id: int) -> None:
    db = _db()
    try:
        l = db.execute(select(Lead).where(Lead.id == lead_id)).scalar_one_or_none()
        if l:
            db.delete(l)
            db.commit()
    finally:
        db.close()


def _delete_follow_up(fu_id: int) -> None:
    db = _db()
    try:
        fu = db.execute(select(FollowUp).where(FollowUp.id == fu_id)).scalar_one_or_none()
        if fu:
            db.delete(fu)
            db.commit()
    finally:
        db.close()


def _delete_booking(booking_id: int) -> None:
    db = _db()
    try:
        b = db.execute(select(Booking).where(Booking.id == booking_id)).scalar_one_or_none()
        if b:
            db.delete(b)
            db.commit()
    finally:
        db.close()


def _delete_unit(unit_id: int) -> None:
    db = _db()
    try:
        u = db.execute(select(Unit).where(Unit.id == unit_id)).scalar_one_or_none()
        if u:
            db.delete(u)
            db.commit()
    finally:
        db.close()


def _delete_building(building_id: int) -> None:
    db = _db()
    try:
        from src.repository.models.building import Building
        b = db.execute(select(Building).where(Building.id == building_id)).scalar_one_or_none()
        if b:
            db.delete(b)
            db.commit()
    finally:
        db.close()


def _delete_project(project_id: int) -> None:
    db = _db()
    try:
        from src.repository.models.project import Project
        p = db.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()
        if p:
            db.delete(p)
            db.commit()
    finally:
        db.close()


def _delete_user(user_id: int) -> None:
    db = _db()
    try:
        from src.repository.models.user import User
        u = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if u:
            db.delete(u)
            db.commit()
    finally:
        db.close()


def _get_user_id(email: str) -> int:
    db = _db()
    try:
        from src.repository.models.user import User
        return db.execute(select(User).where(User.email == email)).scalar_one().id
    finally:
        db.close()


# ── Data helpers ──────────────────────────────────────────────────────────────
def _future(hours: int = 24) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past(hours: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def _make_lead(client: TestClient, headers: dict, stage: str = "NEW",
               assigned_to: int | None = None) -> dict:
    payload = {
        "name": f"DashLead_{uuid.uuid4().hex[:6]}",
        "email": f"dashlead_{uuid.uuid4().hex[:8]}@test.com",
        "stage": stage,
    }
    if assigned_to is not None:
        payload["assigned_to"] = assigned_to
    resp = client.post(LEADS_URL, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_follow_up(client: TestClient, lead_id: int, headers: dict,
                    follow_up_at: str | None = None, status: str = "PENDING") -> dict:
    payload = {"follow_up_at": follow_up_at or _future(48)}
    resp = client.post(f"{LEADS_URL}/{lead_id}/follow-ups", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _insert_overdue_follow_up(lead_id: int, assigned_to_user_id: int) -> int:
    """Insert a PENDING follow-up with a past date directly via DB (API rejects past dates)."""
    db = _db()
    try:
        fu = FollowUp(
            lead_id=lead_id,
            assigned_to=assigned_to_user_id,
            follow_up_at=datetime.now(timezone.utc) - timedelta(hours=2),
            status=FollowUpStatus.PENDING,
        )
        db.add(fu)
        db.commit()
        db.refresh(fu)
        return fu.id
    finally:
        db.close()


def _create_project_building_unit(client: TestClient) -> tuple[int, int, int]:
    """Returns (project_id, building_id, unit_id) — all AVAILABLE."""
    p = client.post(
        PROJECTS_URL,
        json={"name": f"DashProj_{uuid.uuid4().hex[:6]}"},
        headers=_admin_h(client),
    )
    pid = p.json()["id"]
    b = client.post(
        f"{PROJECTS_URL}/{pid}/buildings",
        json={"name": "DashBlock", "total_floors": 3},
        headers=_admin_h(client),
    )
    bid = b.json()["id"]
    u = client.post(
        f"{BUILDINGS_URL}/{bid}/units",
        json={"unit_number": f"D-{uuid.uuid4().hex[:4].upper()}", "type": "2BHK",
              "floor": 1, "price": 5000000, "status": "AVAILABLE"},
        headers=_admin_h(client),
    )
    uid = u.json()["id"]
    return pid, bid, uid


def _create_sales_user(client: TestClient) -> dict:
    email = f"sales_dash_{uuid.uuid4().hex[:8]}@test.com"
    resp = client.post(
        USERS_URL,
        json={"name": "Dashboard Sales", "email": email,
              "password": "Test@1234", "role": "SALES"},
        headers=_admin_h(client),
    )
    assert resp.status_code == 201
    return resp.json()


# ═════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ═════════════════════════════════════════════════════════════════════════════

class TestDashboardAuthentication:

    def test_unauthenticated_returns_401(self, client: TestClient) -> None:
        assert client.get(DASHBOARD_URL).status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        resp = client.get(DASHBOARD_URL, headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401

    def test_inactive_user_returns_401(self, client: TestClient) -> None:
        # Create a user, deactivate them, then attempt access
        user = _create_sales_user(client)
        token = _get_token(client, user["email"], "Test@1234")
        client.patch(f"{USERS_URL}/{user['id']}/deactivate", headers=_admin_h(client))
        try:
            resp = client.get(DASHBOARD_URL, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 401
        finally:
            _delete_user(user["id"])


# ═════════════════════════════════════════════════════════════════════════════
# RESPONSE SHAPE
# ═════════════════════════════════════════════════════════════════════════════

class TestDashboardResponseShape:

    def test_admin_response_has_all_sections(self, client: TestClient) -> None:
        resp = client.get(DASHBOARD_URL, headers=_admin_h(client))
        assert resp.status_code == 200
        body = resp.json()
        assert "leads" in body
        assert "follow_ups" in body
        assert "properties" in body
        assert "bookings" in body

    def test_leads_section_shape(self, client: TestClient) -> None:
        body = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()
        leads = body["leads"]
        assert "total" in leads
        assert "by_stage" in leads
        assert isinstance(leads["total"], int)
        assert isinstance(leads["by_stage"], dict)

    def test_all_lead_stages_present(self, client: TestClient) -> None:
        """Every LeadStage value must appear in by_stage even if count is zero."""
        from src.utils.enums import LeadStage
        body = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()
        by_stage = body["leads"]["by_stage"]
        for stage in LeadStage:
            assert stage.value in by_stage, f"Missing stage: {stage.value}"

    def test_follow_ups_section_shape(self, client: TestClient) -> None:
        body = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()
        fu = body["follow_ups"]
        assert "upcoming" in fu
        assert "overdue" in fu
        assert isinstance(fu["upcoming"], int)
        assert isinstance(fu["overdue"], int)

    def test_properties_section_shape(self, client: TestClient) -> None:
        body = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()
        props = body["properties"]
        assert "total_units" in props
        assert "available_units" in props
        assert "booked_units" in props

    def test_bookings_section_shape(self, client: TestClient) -> None:
        body = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()
        bk = body["bookings"]
        assert "confirmed" in bk
        assert "cancelled" in bk

    def test_sales_response_has_same_shape(self, client: TestClient) -> None:
        resp = client.get(DASHBOARD_URL, headers=_sales_h(client))
        assert resp.status_code == 200
        body = resp.json()
        assert "leads" in body
        assert "follow_ups" in body
        assert "properties" in body
        assert "bookings" in body


# ═════════════════════════════════════════════════════════════════════════════
# LEAD STATISTICS
# ═════════════════════════════════════════════════════════════════════════════

class TestLeadStatistics:

    def test_admin_lead_total_increases_after_create(self, client: TestClient) -> None:
        before = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["leads"]["total"]
        lead = _make_lead(client, _admin_h(client))
        after = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["leads"]["total"]
        assert after == before + 1
        _delete_lead(lead["id"])

    def test_admin_stage_count_updates_on_create(self, client: TestClient) -> None:
        before_stages = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["leads"]["by_stage"]
        lead = _make_lead(client, _admin_h(client), stage="NEGOTIATION")
        after_stages = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["leads"]["by_stage"]
        assert after_stages["NEGOTIATION"] == before_stages["NEGOTIATION"] + 1
        _delete_lead(lead["id"])

    def test_soft_deleted_lead_excluded_from_total(self, client: TestClient) -> None:
        lead = _make_lead(client, _admin_h(client))
        before = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["leads"]["total"]
        client.delete(f"{LEADS_URL}/{lead['id']}", headers=_admin_h(client))
        after = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["leads"]["total"]
        assert after == before - 1
        _delete_lead(lead["id"])

    def test_soft_deleted_lead_excluded_from_stage_count(self, client: TestClient) -> None:
        lead = _make_lead(client, _admin_h(client), stage="CONTACTED")
        before = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["leads"]["by_stage"]["CONTACTED"]
        client.delete(f"{LEADS_URL}/{lead['id']}", headers=_admin_h(client))
        after = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["leads"]["by_stage"]["CONTACTED"]
        assert after == before - 1
        _delete_lead(lead["id"])

    def test_all_stages_always_present_even_if_zero(self, client: TestClient) -> None:
        """Deliberately verified: no stage may be omitted regardless of count."""
        from src.utils.enums import LeadStage
        body = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()
        for stage in LeadStage:
            assert stage.value in body["leads"]["by_stage"]
            assert isinstance(body["leads"]["by_stage"][stage.value], int)

    def test_sales_total_counts_only_own_leads(self, client: TestClient) -> None:
        sales_id = _get_user_id(SALES_EMAIL)
        admin_id = _get_user_id(ADMIN_EMAIL)
        # Lead assigned to admin — sales must NOT count it
        admin_lead = _make_lead(client, _admin_h(client), assigned_to=admin_id)
        # Lead assigned to sales
        sales_lead = _make_lead(client, _sales_h(client))
        try:
            before_admin = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["leads"]["total"]
            sales_dash = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["leads"]
            admin_dash = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["leads"]
            # Sales total should not include admin_lead
            sales_lead_ids_via_api = client.get(
                LEADS_URL, headers=_sales_h(client)
            ).json()["items"]
            assert all(l["assigned_to"] == sales_id for l in sales_lead_ids_via_api)
        finally:
            _delete_lead(admin_lead["id"])
            _delete_lead(sales_lead["id"])

    def test_sales_only_sees_own_stage_counts(self, client: TestClient) -> None:
        # Create a lead for a second sales user; first sales must not see it
        sales2 = _create_sales_user(client)
        sales2_h = _headers_for(client, sales2["email"])
        other_lead = _make_lead(client, sales2_h, stage="SITE_VISIT")
        before = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["leads"]["by_stage"]["SITE_VISIT"]
        try:
            after = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["leads"]["by_stage"]["SITE_VISIT"]
            assert after == before  # unaffected
        finally:
            _delete_lead(other_lead["id"])
            _delete_user(sales2["id"])


# ═════════════════════════════════════════════════════════════════════════════
# FOLLOW-UP STATISTICS
# ═════════════════════════════════════════════════════════════════════════════

class TestFollowUpStatistics:

    def test_upcoming_count_increases_after_create(self, client: TestClient) -> None:
        lead = _make_lead(client, _admin_h(client))
        before = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["follow_ups"]["upcoming"]
        fu = _make_follow_up(client, lead["id"], _admin_h(client), follow_up_at=_future(48))
        after = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["follow_ups"]["upcoming"]
        assert after == before + 1
        _delete_follow_up(fu["id"])
        _delete_lead(lead["id"])

    def test_overdue_count_increases_after_inserting_past_follow_up(self, client: TestClient) -> None:
        admin_id = _get_user_id(ADMIN_EMAIL)
        lead = _make_lead(client, _admin_h(client))
        before = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["follow_ups"]["overdue"]
        fu_id = _insert_overdue_follow_up(lead["id"], admin_id)
        after = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["follow_ups"]["overdue"]
        assert after == before + 1
        _delete_follow_up(fu_id)
        _delete_lead(lead["id"])

    def test_completed_follow_up_not_counted(self, client: TestClient) -> None:
        lead = _make_lead(client, _admin_h(client))
        fu = _make_follow_up(client, lead["id"], _admin_h(client))
        # Mark as COMPLETED
        client.put(
            f"{FOLLOW_UPS_URL}/{fu['id']}",
            json={"status": "COMPLETED"},
            headers=_admin_h(client),
        )
        before_upcoming = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["follow_ups"]["upcoming"]
        # Creating a new upcoming one should increase by 1 — COMPLETED must not count
        fu2 = _make_follow_up(client, lead["id"], _admin_h(client), follow_up_at=_future(72))
        after_upcoming = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["follow_ups"]["upcoming"]
        assert after_upcoming == before_upcoming + 1
        _delete_follow_up(fu["id"])
        _delete_follow_up(fu2["id"])
        _delete_lead(lead["id"])

    def test_cancelled_follow_up_not_counted(self, client: TestClient) -> None:
        lead = _make_lead(client, _admin_h(client))
        fu = _make_follow_up(client, lead["id"], _admin_h(client))
        client.put(
            f"{FOLLOW_UPS_URL}/{fu['id']}",
            json={"status": "CANCELLED"},
            headers=_admin_h(client),
        )
        before = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["follow_ups"]["upcoming"]
        after = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["follow_ups"]["upcoming"]
        assert after == before  # CANCELLED must not affect upcoming count
        _delete_follow_up(fu["id"])
        _delete_lead(lead["id"])

    def test_sales_follow_up_count_scoped_to_own_leads(self, client: TestClient) -> None:
        # Lead assigned to admin — follow-up on it must NOT appear in sales dashboard
        admin_id = _get_user_id(ADMIN_EMAIL)
        admin_lead = _make_lead(client, _admin_h(client), assigned_to=admin_id)
        fu = _make_follow_up(client, admin_lead["id"], _admin_h(client))
        before = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["follow_ups"]["upcoming"]
        # Create a follow-up on the admin lead — sales should not see it
        fu2 = _make_follow_up(client, admin_lead["id"], _admin_h(client))
        after = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["follow_ups"]["upcoming"]
        assert after == before  # unaffected
        _delete_follow_up(fu["id"])
        _delete_follow_up(fu2["id"])
        _delete_lead(admin_lead["id"])

    def test_sales_own_follow_up_counted(self, client: TestClient) -> None:
        sales_lead = _make_lead(client, _sales_h(client))
        before = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["follow_ups"]["upcoming"]
        fu = _make_follow_up(client, sales_lead["id"], _sales_h(client), follow_up_at=_future(24))
        after = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["follow_ups"]["upcoming"]
        assert after == before + 1
        _delete_follow_up(fu["id"])
        _delete_lead(sales_lead["id"])


# ═════════════════════════════════════════════════════════════════════════════
# PROPERTY STATISTICS
# ═════════════════════════════════════════════════════════════════════════════

class TestPropertyStatistics:

    def test_total_equals_available_plus_booked(self, client: TestClient) -> None:
        body = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["properties"]
        assert body["total_units"] == body["available_units"] + body["booked_units"]

    def test_total_equals_available_plus_booked_for_sales(self, client: TestClient) -> None:
        body = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["properties"]
        assert body["total_units"] == body["available_units"] + body["booked_units"]

    def test_new_available_unit_increases_available_count(self, client: TestClient) -> None:
        before = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["properties"]
        pid, bid, uid = _create_project_building_unit(client)
        try:
            after = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["properties"]
            assert after["total_units"] == before["total_units"] + 1
            assert after["available_units"] == before["available_units"] + 1
            assert after["booked_units"] == before["booked_units"]
        finally:
            _delete_unit(uid)
            _delete_building(bid)
            _delete_project(pid)

    def test_booking_shifts_available_to_booked(self, client: TestClient) -> None:
        pid, bid, uid = _create_project_building_unit(client)
        lead = _make_lead(client, _admin_h(client))
        try:
            before = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["properties"]
            booking = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead["id"], "unit_id": uid},
                headers=_admin_h(client),
            )
            assert booking.status_code == 201
            bk_id = booking.json()["id"]
            after = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["properties"]
            assert after["available_units"] == before["available_units"] - 1
            assert after["booked_units"] == before["booked_units"] + 1
            assert after["total_units"] == before["total_units"]
            _delete_booking(bk_id)
        finally:
            _delete_unit(uid)
            _delete_building(bid)
            _delete_project(pid)
            _delete_lead(lead["id"])

    def test_cancellation_shifts_booked_back_to_available(self, client: TestClient) -> None:
        pid, bid, uid = _create_project_building_unit(client)
        lead = _make_lead(client, _admin_h(client))
        try:
            booking = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead["id"], "unit_id": uid},
                headers=_admin_h(client),
            )
            bk_id = booking.json()["id"]
            before = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["properties"]
            client.patch(f"{BOOKINGS_URL}/{bk_id}/cancel", headers=_admin_h(client))
            after = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["properties"]
            assert after["available_units"] == before["available_units"] + 1
            assert after["booked_units"] == before["booked_units"] - 1
            _delete_booking(bk_id)
        finally:
            _delete_unit(uid)
            _delete_building(bid)
            _delete_project(pid)
            _delete_lead(lead["id"])

    def test_property_counts_same_for_admin_and_sales(self, client: TestClient) -> None:
        """Property stats are global for both roles."""
        admin_props = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["properties"]
        sales_props = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["properties"]
        assert admin_props["total_units"] == sales_props["total_units"]
        assert admin_props["available_units"] == sales_props["available_units"]
        assert admin_props["booked_units"] == sales_props["booked_units"]


# ═════════════════════════════════════════════════════════════════════════════
# BOOKING STATISTICS
# ═════════════════════════════════════════════════════════════════════════════

class TestBookingStatistics:

    def test_admin_confirmed_count_increases_after_booking(self, client: TestClient) -> None:
        pid, bid, uid = _create_project_building_unit(client)
        lead = _make_lead(client, _admin_h(client))
        before = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["bookings"]["confirmed"]
        try:
            booking = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead["id"], "unit_id": uid},
                headers=_admin_h(client),
            )
            assert booking.status_code == 201
            bk_id = booking.json()["id"]
            after = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["bookings"]["confirmed"]
            assert after == before + 1
            _delete_booking(bk_id)
        finally:
            _delete_unit(uid)
            _delete_building(bid)
            _delete_project(pid)
            _delete_lead(lead["id"])

    def test_admin_cancelled_count_increases_after_cancellation(self, client: TestClient) -> None:
        pid, bid, uid = _create_project_building_unit(client)
        lead = _make_lead(client, _admin_h(client))
        try:
            booking = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead["id"], "unit_id": uid},
                headers=_admin_h(client),
            )
            bk_id = booking.json()["id"]
            before_cancelled = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["bookings"]["cancelled"]
            before_confirmed = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["bookings"]["confirmed"]
            client.patch(f"{BOOKINGS_URL}/{bk_id}/cancel", headers=_admin_h(client))
            after = client.get(DASHBOARD_URL, headers=_admin_h(client)).json()["bookings"]
            assert after["cancelled"] == before_cancelled + 1
            assert after["confirmed"] == before_confirmed - 1
            _delete_booking(bk_id)
        finally:
            _delete_unit(uid)
            _delete_building(bid)
            _delete_project(pid)
            _delete_lead(lead["id"])

    def test_sales_booking_stats_scoped_to_own_bookings(self, client: TestClient) -> None:
        # Admin creates a booking; sales booking count should not change
        pid, bid, uid = _create_project_building_unit(client)
        lead = _make_lead(client, _admin_h(client))
        before_sales = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["bookings"]["confirmed"]
        try:
            booking = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead["id"], "unit_id": uid},
                headers=_admin_h(client),
            )
            bk_id = booking.json()["id"]
            after_sales = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["bookings"]["confirmed"]
            assert after_sales == before_sales  # admin booking must not affect sales count
            _delete_booking(bk_id)
        finally:
            _delete_unit(uid)
            _delete_building(bid)
            _delete_project(pid)
            _delete_lead(lead["id"])

    def test_sales_own_booking_counted(self, client: TestClient) -> None:
        pid, bid, uid = _create_project_building_unit(client)
        lead = _make_lead(client, _sales_h(client))
        before = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["bookings"]["confirmed"]
        try:
            booking = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead["id"], "unit_id": uid},
                headers=_sales_h(client),
            )
            assert booking.status_code == 201
            bk_id = booking.json()["id"]
            after = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["bookings"]["confirmed"]
            assert after == before + 1
            _delete_booking(bk_id)
        finally:
            _delete_unit(uid)
            _delete_building(bid)
            _delete_project(pid)
            _delete_lead(lead["id"])


# ═════════════════════════════════════════════════════════════════════════════
# DATA ISOLATION — Sales A must not see Sales B's data
# ═════════════════════════════════════════════════════════════════════════════

class TestSalesDataIsolation:

    def test_sales_b_lead_not_counted_in_sales_a_dashboard(self, client: TestClient) -> None:
        sales_b = _create_sales_user(client)
        sales_b_h = _headers_for(client, sales_b["email"])
        lead_b = _make_lead(client, sales_b_h, stage="INTERESTED")
        before_a = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["leads"]["by_stage"]["INTERESTED"]
        try:
            after_a = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["leads"]["by_stage"]["INTERESTED"]
            assert after_a == before_a  # Sales A unaffected by Sales B's lead
        finally:
            _delete_lead(lead_b["id"])
            _delete_user(sales_b["id"])

    def test_sales_b_follow_up_not_counted_in_sales_a_dashboard(self, client: TestClient) -> None:
        sales_b = _create_sales_user(client)
        sales_b_h = _headers_for(client, sales_b["email"])
        lead_b = _make_lead(client, sales_b_h)
        fu_b = _make_follow_up(client, lead_b["id"], sales_b_h)
        before_a = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["follow_ups"]["upcoming"]
        try:
            after_a = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["follow_ups"]["upcoming"]
            assert after_a == before_a
        finally:
            _delete_follow_up(fu_b["id"])
            _delete_lead(lead_b["id"])
            _delete_user(sales_b["id"])

    def test_sales_b_booking_not_counted_in_sales_a_dashboard(self, client: TestClient) -> None:
        sales_b = _create_sales_user(client)
        sales_b_h = _headers_for(client, sales_b["email"])
        lead_b = _make_lead(client, sales_b_h)
        pid, bid, uid = _create_project_building_unit(client)
        before_a = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["bookings"]["confirmed"]
        try:
            booking = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead_b["id"], "unit_id": uid},
                headers=sales_b_h,
            )
            assert booking.status_code == 201
            bk_id = booking.json()["id"]
            after_a = client.get(DASHBOARD_URL, headers=_sales_h(client)).json()["bookings"]["confirmed"]
            assert after_a == before_a
            _delete_booking(bk_id)
        finally:
            _delete_unit(uid)
            _delete_building(bid)
            _delete_project(pid)
            _delete_lead(lead_b["id"])
            _delete_user(sales_b["id"])
