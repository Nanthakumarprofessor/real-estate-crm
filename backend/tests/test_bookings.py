"""
Phase 7 — Booking Workflow tests.

Covers:
  Authentication  (401 on all endpoints without token)
  Authorization   (Admin vs Sales permissions, ownership isolation)
  Validation      (nonexistent lead/unit, inactive lead, negative amount, 422)
  Booking state   (unit BOOKED, lead stage BOOKED, booking CONFIRMED after create)
  Cancellation    (unit AVAILABLE, booking CANCELLED, record preserved, 409 on re-cancel)
  Concurrency     (double-booking the same unit returns 409; DB index integrity)
  Listing/filtering (pagination, status filter, lead_id filter, unit_id filter)

Strategy for concurrency test:
  We cannot easily run two simultaneous HTTP requests through TestClient in a
  single-threaded pytest run.  Instead we prove the two-layer defence directly:

  Layer 1 — We submit a second API booking request after the first has already
             set unit.status = BOOKED.  The service rejects it with 409 because
             SELECT FOR UPDATE sees BOOKED status.

  Layer 2 — We directly attempt to INSERT a duplicate CONFIRMED booking row via
             a raw DB session and verify that the partial unique index
             (uix_unit_confirmed_booking) raises IntegrityError.

  Together these tests prove that neither the application logic nor the database
  layer will allow two CONFIRMED bookings for the same unit.

Test isolation:
  Each test that mutates DB state cleans up after itself.
  We use seeded units (A-101 type units) from Phase 2 seed that are still
  AVAILABLE, plus freshly created units/leads to avoid cross-test pollution.
"""
import threading
import uuid
import warnings

warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.main import app
from src.repository.database import SessionLocal
from src.repository.models.booking import Booking
from src.repository.models.lead import Lead
from src.repository.models.unit import Unit
from src.utils.enums import BookingStatus, LeadStage, UnitStatus

# ── URLs ──────────────────────────────────────────────────────────────────────
BOOKINGS_URL = "/api/bookings"
LEADS_URL = "/api/leads"
PROJECTS_URL = "/api/projects"
BUILDINGS_URL = "/api/buildings"
UNITS_URL = "/api/units"
LOGIN_URL = "/api/auth/login"

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


# ── DB helpers ────────────────────────────────────────────────────────────────
def _db():
    return SessionLocal()


def _get_sales_user_id() -> int:
    db = _db()
    try:
        from src.repository.models.user import User
        return db.execute(select(User).where(User.email == SALES_EMAIL)).scalar_one().id
    finally:
        db.close()


def _get_admin_user_id() -> int:
    db = _db()
    try:
        from src.repository.models.user import User
        return db.execute(select(User).where(User.email == ADMIN_EMAIL)).scalar_one().id
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


def _delete_lead(lead_id: int) -> None:
    db = _db()
    try:
        l = db.execute(select(Lead).where(Lead.id == lead_id)).scalar_one_or_none()
        if l:
            db.delete(l)
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


def _reset_unit_to_available(unit_id: int) -> None:
    db = _db()
    try:
        unit = db.execute(select(Unit).where(Unit.id == unit_id)).scalar_one_or_none()
        if unit:
            unit.status = UnitStatus.AVAILABLE
            db.commit()
    finally:
        db.close()


def _reset_lead_stage(lead_id: int, stage: str = "NEW") -> None:
    db = _db()
    try:
        lead = db.execute(select(Lead).where(Lead.id == lead_id)).scalar_one_or_none()
        if lead:
            lead.stage = stage
            db.commit()
    finally:
        db.close()


# ── Test data factories ───────────────────────────────────────────────────────
def _create_fresh_lead(client: TestClient, headers: dict, assigned_to: int | None = None) -> dict:
    payload = {
        "name": f"Lead_{uuid.uuid4().hex[:8]}",
        "email": f"lead_{uuid.uuid4().hex[:8]}@test.com",
        "stage": "NEW",
    }
    if assigned_to is not None:
        payload["assigned_to"] = assigned_to
    resp = client.post(LEADS_URL, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_fresh_unit(client: TestClient, building_id: int) -> dict:
    payload = {
        "unit_number": f"T-{uuid.uuid4().hex[:6].upper()}",
        "type": "2BHK",
        "floor": 1,
        "price": 5000000,
        "status": "AVAILABLE",
    }
    resp = client.post(f"{BUILDINGS_URL}/{building_id}/units", json=payload, headers=_admin_h(client))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_project_and_building(client: TestClient) -> tuple[int, int]:
    """Returns (project_id, building_id)."""
    p = client.post(
        PROJECTS_URL,
        json={"name": f"TestProj_{uuid.uuid4().hex[:6]}"},
        headers=_admin_h(client),
    )
    assert p.status_code == 201
    pid = p.json()["id"]
    b = client.post(
        f"{PROJECTS_URL}/{pid}/buildings",
        json={"name": "TestBlock", "total_floors": 5},
        headers=_admin_h(client),
    )
    assert b.status_code == 201
    return pid, b.json()["id"]


# ── Module-scoped shared project/building for efficiency ─────────────────────
@pytest.fixture(scope="module")
def shared_building(client: TestClient):
    """One project + building reused across most tests; cleaned up at end."""
    pid, bid = _create_project_and_building(client)
    yield bid
    _delete_building(bid)
    _delete_project(pid)


# ═════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION — 401 on all endpoints without a token
# ═════════════════════════════════════════════════════════════════════════════

class TestBookingAuthentication:

    def test_unauthenticated_create(self, client: TestClient) -> None:
        resp = client.post(BOOKINGS_URL, json={"lead_id": 1, "unit_id": 1})
        assert resp.status_code == 401

    def test_unauthenticated_list(self, client: TestClient) -> None:
        assert client.get(BOOKINGS_URL).status_code == 401

    def test_unauthenticated_get(self, client: TestClient) -> None:
        assert client.get(f"{BOOKINGS_URL}/1").status_code == 401

    def test_unauthenticated_cancel(self, client: TestClient) -> None:
        assert client.patch(f"{BOOKINGS_URL}/1/cancel").status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# AUTHORIZATION
# ═════════════════════════════════════════════════════════════════════════════

class TestBookingAuthorization:

    def test_sales_cannot_cancel(self, client: TestClient, shared_building: int) -> None:
        # Create a booking, then try to cancel as sales
        lead = _create_fresh_lead(client, _sales_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking_resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_sales_h(client),
        )
        assert booking_resp.status_code == 201
        bid = booking_resp.json()["id"]
        try:
            cancel = client.patch(f"{BOOKINGS_URL}/{bid}/cancel", headers=_sales_h(client))
            assert cancel.status_code == 403
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_admin_can_cancel(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking_resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        assert booking_resp.status_code == 201
        bid = booking_resp.json()["id"]
        try:
            cancel = client.patch(f"{BOOKINGS_URL}/{bid}/cancel", headers=_admin_h(client))
            assert cancel.status_code == 200
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_sales_cannot_book_another_users_lead(self, client: TestClient, shared_building: int) -> None:
        # Create a lead assigned to admin, then sales tries to book it
        admin_id = _get_admin_user_id()
        lead = _create_fresh_lead(client, _admin_h(client), assigned_to=admin_id)
        unit = _create_fresh_unit(client, shared_building)
        try:
            resp = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead["id"], "unit_id": unit["id"]},
                headers=_sales_h(client),
            )
            assert resp.status_code == 403
        finally:
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_sales_cannot_view_another_users_booking(self, client: TestClient, shared_building: int) -> None:
        # Admin creates a booking; sales tries to read it
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking_resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        assert booking_resp.status_code == 201
        bid = booking_resp.json()["id"]
        try:
            resp = client.get(f"{BOOKINGS_URL}/{bid}", headers=_sales_h(client))
            assert resp.status_code == 403
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_admin_can_view_any_booking(self, client: TestClient, shared_building: int) -> None:
        sales_id = _get_sales_user_id()
        lead = _create_fresh_lead(client, _sales_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking_resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_sales_h(client),
        )
        assert booking_resp.status_code == 201
        bid = booking_resp.json()["id"]
        try:
            resp = client.get(f"{BOOKINGS_URL}/{bid}", headers=_admin_h(client))
            assert resp.status_code == 200
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])


# ═════════════════════════════════════════════════════════════════════════════
# BOOKING CREATION — Happy paths
# ═════════════════════════════════════════════════════════════════════════════

class TestBookingCreation:

    def test_admin_can_create_booking(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"], "amount": 5000000},
            headers=_admin_h(client),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["lead_id"] == lead["id"]
        assert body["unit_id"] == unit["id"]
        assert body["status"] == "CONFIRMED"
        assert float(body["amount"]) == 5000000.0
        assert "booking_date" in body
        assert "id" in body
        _delete_booking(body["id"])
        _delete_unit(unit["id"])
        _delete_lead(lead["id"])

    def test_sales_can_create_booking_for_own_lead(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _sales_h(client))
        unit = _create_fresh_unit(client, shared_building)
        resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_sales_h(client),
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "CONFIRMED"
        _delete_booking(resp.json()["id"])
        _delete_unit(unit["id"])
        _delete_lead(lead["id"])

    def test_booking_without_amount_is_accepted(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        assert resp.status_code == 201
        assert resp.json()["amount"] is None
        _delete_booking(resp.json()["id"])
        _delete_unit(unit["id"])
        _delete_lead(lead["id"])

    def test_booking_date_is_not_client_settable(self, client: TestClient, shared_building: int) -> None:
        """booking_date in request body must be ignored — server generates it."""
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        resp = client.post(
            BOOKINGS_URL,
            json={
                "lead_id": lead["id"],
                "unit_id": unit["id"],
                "booking_date": "2000-01-01T00:00:00Z",  # must be ignored
            },
            headers=_admin_h(client),
        )
        assert resp.status_code == 201
        # booking_date should be recent (within the last minute), not year 2000
        from datetime import datetime, timezone, timedelta
        bd = datetime.fromisoformat(resp.json()["booking_date"].replace("Z", "+00:00"))
        assert bd > datetime.now(timezone.utc) - timedelta(minutes=2)
        _delete_booking(resp.json()["id"])
        _delete_unit(unit["id"])
        _delete_lead(lead["id"])


# ═════════════════════════════════════════════════════════════════════════════
# BOOKING STATE TRANSITIONS
# ═════════════════════════════════════════════════════════════════════════════

class TestBookingStateTransitions:

    def test_booking_sets_unit_status_to_booked(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        assert unit["status"] == "AVAILABLE"
        booking_resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        assert booking_resp.status_code == 201
        bid = booking_resp.json()["id"]
        try:
            # Verify via DB
            db = _db()
            try:
                u = db.execute(select(Unit).where(Unit.id == unit["id"])).scalar_one()
                assert u.status == UnitStatus.BOOKED
            finally:
                db.close()
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_booking_sets_lead_stage_to_booked(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking_resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        assert booking_resp.status_code == 201
        bid = booking_resp.json()["id"]
        try:
            db = _db()
            try:
                l = db.execute(select(Lead).where(Lead.id == lead["id"])).scalar_one()
                assert l.stage == LeadStage.BOOKED
            finally:
                db.close()
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_booking_status_is_confirmed(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        assert resp.status_code == 201
        bid = resp.json()["id"]
        try:
            assert resp.json()["status"] == "CONFIRMED"
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_cancellation_sets_unit_back_to_available(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking_resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        bid = booking_resp.json()["id"]
        try:
            cancel = client.patch(f"{BOOKINGS_URL}/{bid}/cancel", headers=_admin_h(client))
            assert cancel.status_code == 200
            assert cancel.json()["status"] == "CANCELLED"
            # Unit must be AVAILABLE again
            db = _db()
            try:
                u = db.execute(select(Unit).where(Unit.id == unit["id"])).scalar_one()
                assert u.status == UnitStatus.AVAILABLE
            finally:
                db.close()
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_cancellation_does_not_change_lead_stage(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking_resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        bid = booking_resp.json()["id"]
        try:
            client.patch(f"{BOOKINGS_URL}/{bid}/cancel", headers=_admin_h(client))
            db = _db()
            try:
                l = db.execute(select(Lead).where(Lead.id == lead["id"])).scalar_one()
                # Stage stays BOOKED — cancellation does not revert it
                assert l.stage == LeadStage.BOOKED
            finally:
                db.close()
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_booking_record_remains_after_cancellation(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking_resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        bid = booking_resp.json()["id"]
        try:
            client.patch(f"{BOOKINGS_URL}/{bid}/cancel", headers=_admin_h(client))
            # Record still exists in DB
            db = _db()
            try:
                b = db.execute(select(Booking).where(Booking.id == bid)).scalar_one_or_none()
                assert b is not None
                assert b.status == BookingStatus.CANCELLED
            finally:
                db.close()
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_cancel_already_cancelled_booking_returns_409(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking_resp = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        bid = booking_resp.json()["id"]
        try:
            client.patch(f"{BOOKINGS_URL}/{bid}/cancel", headers=_admin_h(client))
            resp2 = client.patch(f"{BOOKINGS_URL}/{bid}/cancel", headers=_admin_h(client))
            assert resp2.status_code == 409
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_cancelled_unit_can_be_rebooked(self, client: TestClient, shared_building: int) -> None:
        """After cancellation, unit is AVAILABLE — a new booking should succeed."""
        lead1 = _create_fresh_lead(client, _admin_h(client))
        lead2 = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        b1 = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead1["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        bid1 = b1.json()["id"]
        client.patch(f"{BOOKINGS_URL}/{bid1}/cancel", headers=_admin_h(client))
        # Now re-book the same unit
        b2 = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead2["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        try:
            assert b2.status_code == 201
            assert b2.json()["status"] == "CONFIRMED"
        finally:
            _delete_booking(bid1)
            _delete_booking(b2.json()["id"])
            _delete_unit(unit["id"])
            _delete_lead(lead1["id"])
            _delete_lead(lead2["id"])


# ═════════════════════════════════════════════════════════════════════════════
# VALIDATION ERRORS
# ═════════════════════════════════════════════════════════════════════════════

class TestBookingValidation:

    def test_nonexistent_lead_returns_404(self, client: TestClient, shared_building: int) -> None:
        unit = _create_fresh_unit(client, shared_building)
        try:
            resp = client.post(
                BOOKINGS_URL,
                json={"lead_id": 999999, "unit_id": unit["id"]},
                headers=_admin_h(client),
            )
            assert resp.status_code == 404
        finally:
            _delete_unit(unit["id"])

    def test_nonexistent_unit_returns_404(self, client: TestClient) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        try:
            resp = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead["id"], "unit_id": 999999},
                headers=_admin_h(client),
            )
            assert resp.status_code == 404
        finally:
            _delete_lead(lead["id"])

    def test_inactive_lead_returns_400(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        # Soft-delete the lead
        client.delete(f"{LEADS_URL}/{lead['id']}", headers=_admin_h(client))
        try:
            resp = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead["id"], "unit_id": unit["id"]},
                headers=_admin_h(client),
            )
            assert resp.status_code == 400
            assert resp.json()["error_code"] == "LEAD_INACTIVE"
        finally:
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_already_booked_unit_returns_409(self, client: TestClient, shared_building: int) -> None:
        lead1 = _create_fresh_lead(client, _admin_h(client))
        lead2 = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        b1 = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead1["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        assert b1.status_code == 201
        bid1 = b1.json()["id"]
        try:
            b2 = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead2["id"], "unit_id": unit["id"]},
                headers=_admin_h(client),
            )
            assert b2.status_code == 409
        finally:
            _delete_booking(bid1)
            _delete_unit(unit["id"])
            _delete_lead(lead1["id"])
            _delete_lead(lead2["id"])

    def test_negative_amount_returns_422(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        try:
            resp = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead["id"], "unit_id": unit["id"], "amount": -500},
                headers=_admin_h(client),
            )
            assert resp.status_code == 422
        finally:
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_missing_lead_id_returns_422(self, client: TestClient, shared_building: int) -> None:
        unit = _create_fresh_unit(client, shared_building)
        try:
            resp = client.post(
                BOOKINGS_URL,
                json={"unit_id": unit["id"]},
                headers=_admin_h(client),
            )
            assert resp.status_code == 422
        finally:
            _delete_unit(unit["id"])

    def test_missing_unit_id_returns_422(self, client: TestClient) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        try:
            resp = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead["id"]},
                headers=_admin_h(client),
            )
            assert resp.status_code == 422
        finally:
            _delete_lead(lead["id"])

    def test_cancel_nonexistent_booking_returns_404(self, client: TestClient) -> None:
        resp = client.patch(f"{BOOKINGS_URL}/999999/cancel", headers=_admin_h(client))
        assert resp.status_code == 404

    def test_get_nonexistent_booking_returns_404(self, client: TestClient) -> None:
        resp = client.get(f"{BOOKINGS_URL}/999999", headers=_admin_h(client))
        assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# LISTING AND FILTERING
# ═════════════════════════════════════════════════════════════════════════════

class TestBookingListing:

    def test_list_response_shape(self, client: TestClient) -> None:
        resp = client.get(BOOKINGS_URL, headers=_admin_h(client))
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "size" in body

    def test_pagination(self, client: TestClient) -> None:
        resp = client.get(f"{BOOKINGS_URL}?page=1&size=2", headers=_admin_h(client))
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 2
        assert body["page"] == 1
        assert body["size"] == 2

    def test_status_filter_confirmed(self, client: TestClient) -> None:
        resp = client.get(f"{BOOKINGS_URL}?status=CONFIRMED", headers=_admin_h(client))
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "CONFIRMED"

    def test_status_filter_cancelled(self, client: TestClient) -> None:
        resp = client.get(f"{BOOKINGS_URL}?status=CANCELLED", headers=_admin_h(client))
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "CANCELLED"

    def test_lead_id_filter(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        bid = booking.json()["id"]
        try:
            resp = client.get(
                f"{BOOKINGS_URL}?lead_id={lead['id']}",
                headers=_admin_h(client),
            )
            assert resp.status_code == 200
            ids = [i["lead_id"] for i in resp.json()["items"]]
            assert all(i == lead["id"] for i in ids)
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_unit_id_filter(self, client: TestClient, shared_building: int) -> None:
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        bid = booking.json()["id"]
        try:
            resp = client.get(
                f"{BOOKINGS_URL}?unit_id={unit['id']}",
                headers=_admin_h(client),
            )
            assert resp.status_code == 200
            unit_ids = [i["unit_id"] for i in resp.json()["items"]]
            assert unit["id"] in unit_ids
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_sales_only_sees_own_bookings(self, client: TestClient, shared_building: int) -> None:
        # Admin creates a booking → sales should NOT see it in their list
        lead = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        bid = booking.json()["id"]
        try:
            resp = client.get(BOOKINGS_URL, headers=_sales_h(client))
            assert resp.status_code == 200
            bids = [i["id"] for i in resp.json()["items"]]
            assert bid not in bids
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])

    def test_admin_can_list_all_bookings(self, client: TestClient, shared_building: int) -> None:
        # Create a booking as sales, verify admin can see it
        lead = _create_fresh_lead(client, _sales_h(client))
        unit = _create_fresh_unit(client, shared_building)
        booking = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead["id"], "unit_id": unit["id"]},
            headers=_sales_h(client),
        )
        bid = booking.json()["id"]
        try:
            resp = client.get(BOOKINGS_URL, headers=_admin_h(client))
            assert resp.status_code == 200
            bids = [i["id"] for i in resp.json()["items"]]
            assert bid in bids
        finally:
            _delete_booking(bid)
            _delete_unit(unit["id"])
            _delete_lead(lead["id"])


# ═════════════════════════════════════════════════════════════════════════════
# CONCURRENCY / DOUBLE-BOOKING PREVENTION
# ═════════════════════════════════════════════════════════════════════════════

class TestBookingConcurrency:

    def test_second_booking_attempt_on_booked_unit_returns_409(
        self, client: TestClient, shared_building: int
    ) -> None:
        """
        Layer 1 proof: after the first booking succeeds, the unit.status is BOOKED.
        The service's SELECT FOR UPDATE path sees BOOKED and returns 409.
        """
        lead1 = _create_fresh_lead(client, _admin_h(client))
        lead2 = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        b1 = client.post(
            BOOKINGS_URL,
            json={"lead_id": lead1["id"], "unit_id": unit["id"]},
            headers=_admin_h(client),
        )
        assert b1.status_code == 201, b1.text
        bid1 = b1.json()["id"]
        try:
            b2 = client.post(
                BOOKINGS_URL,
                json={"lead_id": lead2["id"], "unit_id": unit["id"]},
                headers=_admin_h(client),
            )
            assert b2.status_code == 409
            assert b2.json()["error_code"] in (
                "BOOKING_UNIT_ALREADY_BOOKED",
                "RESOURCE_ALREADY_EXISTS",
            )
        finally:
            _delete_booking(bid1)
            _delete_unit(unit["id"])
            _delete_lead(lead1["id"])
            _delete_lead(lead2["id"])

    def test_partial_unique_index_prevents_duplicate_confirmed_bookings(
        self, client: TestClient, shared_building: int
    ) -> None:
        """
        Layer 2 proof: directly attempt to INSERT two CONFIRMED bookings for the
        same unit via raw DB sessions. The partial unique index
        uix_unit_confirmed_booking must raise IntegrityError on the second insert.
        """
        lead1 = _create_fresh_lead(client, _admin_h(client))
        lead2 = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        admin_id = _get_admin_user_id()

        db = _db()
        b1_id = None
        try:
            # First CONFIRMED booking — must succeed
            b1 = Booking(
                lead_id=lead1["id"],
                unit_id=unit["id"],
                booked_by=admin_id,
                status=BookingStatus.CONFIRMED,
            )
            db.add(b1)
            db.flush()
            b1_id = b1.id

            # Second CONFIRMED booking for the SAME unit — must raise IntegrityError
            b2 = Booking(
                lead_id=lead2["id"],
                unit_id=unit["id"],
                booked_by=admin_id,
                status=BookingStatus.CONFIRMED,
            )
            db.add(b2)
            with pytest.raises(IntegrityError):
                db.flush()

            db.rollback()
        finally:
            db.close()

        # Clean up the first booking if it was inserted
        if b1_id:
            _delete_booking(b1_id)
        _delete_unit(unit["id"])
        _delete_lead(lead1["id"])
        _delete_lead(lead2["id"])

    def test_concurrent_booking_threads_only_one_succeeds(
        self, client: TestClient, shared_building: int
    ) -> None:
        """
        Simulate two concurrent booking requests using threads.
        Only one should succeed (201); the other must fail (409 or 500).
        This exercises the SELECT FOR UPDATE path under real concurrency.
        """
        lead1 = _create_fresh_lead(client, _admin_h(client))
        lead2 = _create_fresh_lead(client, _admin_h(client))
        unit = _create_fresh_unit(client, shared_building)
        results = []

        def book(lead_id: int) -> None:
            # Each thread needs its own TestClient instance for isolation
            with TestClient(app, raise_server_exceptions=False) as c:
                token = _get_token(c, ADMIN_EMAIL, ADMIN_PASSWORD)
                r = c.post(
                    BOOKINGS_URL,
                    json={"lead_id": lead_id, "unit_id": unit["id"]},
                    headers={"Authorization": f"Bearer {token}"},
                )
                results.append(r.status_code)

        t1 = threading.Thread(target=book, args=(lead1["id"],))
        t2 = threading.Thread(target=book, args=(lead2["id"],))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        successes = results.count(201)
        failures = [s for s in results if s != 201]

        assert successes == 1, f"Expected exactly 1 success, got results={results}"
        assert len(failures) == 1
        assert failures[0] in (409, 500), f"Expected 409 conflict, got {failures[0]}"

        # Clean up — find the booking that was created
        db = _db()
        try:
            bookings = db.execute(
                select(Booking).where(Booking.unit_id == unit["id"])
            ).scalars().all()
            for b in bookings:
                db.delete(b)
            db.commit()
        finally:
            db.close()

        _delete_unit(unit["id"])
        _delete_lead(lead1["id"])
        _delete_lead(lead2["id"])
