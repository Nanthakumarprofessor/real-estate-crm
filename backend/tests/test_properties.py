"""
Phase 6 — Property Management API tests.

Covers:
  Authorization (unauthenticated → 401, Sales mutation → 403, Admin → allowed)
  Project CRUD (create, list, get, update, delete, search, pagination)
  Building CRUD (create under project, list, get, update, delete)
  Unit CRUD (create under building, list, get, update, delete)
  Dependency-aware deletion (project with buildings → 409, building with units → 409,
                              unit with bookings → 409)
  Validation (empty names, invalid enums, negative price, duplicate unit numbers)
  Cross-building uniqueness (same unit_number in different buildings is allowed)

All tests create and clean up their own data via DB helpers so the test suite
is safe to run against the shared development database.
"""
import uuid
import warnings

warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from src.main import app
from src.repository.database import SessionLocal
from src.repository.models.building import Building
from src.repository.models.project import Project
from src.repository.models.unit import Unit

# ── URLs ──────────────────────────────────────────────────────────────────────
PROJECTS_URL = "/api/projects"
BUILDINGS_URL = "/api/buildings"
UNITS_URL = "/api/units"
LOGIN_URL = "/api/auth/login"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@123"
SALES_EMAIL = "sales@example.com"
SALES_PASSWORD = "Sales@123"


# ── Shared client ─────────────────────────────────────────────────────────────
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


# ── DB cleanup helpers ────────────────────────────────────────────────────────
def _delete_project(project_id: int) -> None:
    db = SessionLocal()
    try:
        p = db.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()
        if p:
            db.delete(p)
            db.commit()
    finally:
        db.close()


def _delete_building(building_id: int) -> None:
    db = SessionLocal()
    try:
        b = db.execute(select(Building).where(Building.id == building_id)).scalar_one_or_none()
        if b:
            db.delete(b)
            db.commit()
    finally:
        db.close()


def _delete_unit(unit_id: int) -> None:
    db = SessionLocal()
    try:
        u = db.execute(select(Unit).where(Unit.id == unit_id)).scalar_one_or_none()
        if u:
            db.delete(u)
            db.commit()
    finally:
        db.close()


# ── Payload helpers ───────────────────────────────────────────────────────────
def _project_payload(**overrides) -> dict:
    defaults = {
        "name": f"Project_{uuid.uuid4().hex[:8]}",
        "location": "Test City",
        "description": "Test project",
    }
    defaults.update(overrides)
    return defaults


def _building_payload(**overrides) -> dict:
    defaults = {"name": f"Building_{uuid.uuid4().hex[:6]}", "total_floors": 5}
    defaults.update(overrides)
    return defaults


def _unit_payload(**overrides) -> dict:
    defaults = {
        "unit_number": f"U-{uuid.uuid4().hex[:4].upper()}",
        "type": "2BHK",
        "floor": 1,
        "price": 5000000,
        "status": "AVAILABLE",
    }
    defaults.update(overrides)
    return defaults


# ── Shared fixture: a project that lives for the whole module ─────────────────
@pytest.fixture(scope="module")
def seeded_project(client: TestClient) -> dict:
    """Create one project for building/unit tests; cleaned up after module."""
    resp = client.post(PROJECTS_URL, json=_project_payload(name="SeedProject"), headers=_admin_h(client))
    assert resp.status_code == 201
    project = resp.json()
    yield project
    _delete_project(project["id"])


@pytest.fixture(scope="module")
def seeded_building(client: TestClient, seeded_project: dict) -> dict:
    """Create one building for unit tests; cleaned up after module."""
    resp = client.post(
        f"{PROJECTS_URL}/{seeded_project['id']}/buildings",
        json=_building_payload(name="SeedBuilding"),
        headers=_admin_h(client),
    )
    assert resp.status_code == 201
    building = resp.json()
    yield building
    _delete_building(building["id"])


# ═════════════════════════════════════════════════════════════════════════════
# AUTHORIZATION
# ═════════════════════════════════════════════════════════════════════════════

class TestPropertyAuthorization:

    def test_unauthenticated_cannot_list_projects(self, client: TestClient) -> None:
        assert client.get(PROJECTS_URL).status_code == 401

    def test_unauthenticated_cannot_create_project(self, client: TestClient) -> None:
        assert client.post(PROJECTS_URL, json=_project_payload()).status_code == 401

    def test_sales_cannot_create_project(self, client: TestClient) -> None:
        assert client.post(PROJECTS_URL, json=_project_payload(), headers=_sales_h(client)).status_code == 403

    def test_sales_cannot_update_project(self, client: TestClient, seeded_project: dict) -> None:
        resp = client.put(
            f"{PROJECTS_URL}/{seeded_project['id']}",
            json={"name": "Hacked"},
            headers=_sales_h(client),
        )
        assert resp.status_code == 403

    def test_sales_cannot_delete_project(self, client: TestClient, seeded_project: dict) -> None:
        assert client.delete(f"{PROJECTS_URL}/{seeded_project['id']}", headers=_sales_h(client)).status_code == 403

    def test_sales_can_list_projects(self, client: TestClient) -> None:
        assert client.get(PROJECTS_URL, headers=_sales_h(client)).status_code == 200

    def test_sales_can_get_project(self, client: TestClient, seeded_project: dict) -> None:
        assert client.get(f"{PROJECTS_URL}/{seeded_project['id']}", headers=_sales_h(client)).status_code == 200

    def test_sales_cannot_create_building(self, client: TestClient, seeded_project: dict) -> None:
        resp = client.post(
            f"{PROJECTS_URL}/{seeded_project['id']}/buildings",
            json=_building_payload(),
            headers=_sales_h(client),
        )
        assert resp.status_code == 403

    def test_sales_can_list_buildings(self, client: TestClient, seeded_project: dict) -> None:
        resp = client.get(f"{PROJECTS_URL}/{seeded_project['id']}/buildings", headers=_sales_h(client))
        assert resp.status_code == 200

    def test_sales_cannot_update_building(self, client: TestClient, seeded_building: dict) -> None:
        resp = client.put(
            f"{BUILDINGS_URL}/{seeded_building['id']}",
            json={"name": "Hacked"},
            headers=_sales_h(client),
        )
        assert resp.status_code == 403

    def test_sales_cannot_delete_building(self, client: TestClient, seeded_building: dict) -> None:
        assert client.delete(f"{BUILDINGS_URL}/{seeded_building['id']}", headers=_sales_h(client)).status_code == 403

    def test_sales_can_get_building(self, client: TestClient, seeded_building: dict) -> None:
        assert client.get(f"{BUILDINGS_URL}/{seeded_building['id']}", headers=_sales_h(client)).status_code == 200

    def test_sales_can_list_units(self, client: TestClient, seeded_building: dict) -> None:
        resp = client.get(f"{BUILDINGS_URL}/{seeded_building['id']}/units", headers=_sales_h(client))
        assert resp.status_code == 200

    def test_sales_cannot_create_unit(self, client: TestClient, seeded_building: dict) -> None:
        resp = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(),
            headers=_sales_h(client),
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list_units(self, client: TestClient, seeded_building: dict) -> None:
        assert client.get(f"{BUILDINGS_URL}/{seeded_building['id']}/units").status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# PROJECT CRUD
# ═════════════════════════════════════════════════════════════════════════════

class TestProjectCRUD:

    def test_admin_can_create_project(self, client: TestClient) -> None:
        payload = _project_payload()
        resp = client.post(PROJECTS_URL, json=payload, headers=_admin_h(client))
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == payload["name"]
        assert body["location"] == payload["location"]
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body
        _delete_project(body["id"])

    def test_create_project_minimal(self, client: TestClient) -> None:
        """Only name is required."""
        resp = client.post(PROJECTS_URL, json={"name": "Minimal Project"}, headers=_admin_h(client))
        assert resp.status_code == 201
        body = resp.json()
        assert body["location"] is None
        assert body["description"] is None
        _delete_project(body["id"])

    def test_create_project_empty_name_returns_422(self, client: TestClient) -> None:
        resp = client.post(PROJECTS_URL, json={"name": "   "}, headers=_admin_h(client))
        assert resp.status_code == 422

    def test_create_project_missing_name_returns_422(self, client: TestClient) -> None:
        resp = client.post(PROJECTS_URL, json={"location": "Mumbai"}, headers=_admin_h(client))
        assert resp.status_code == 422

    def test_admin_can_list_projects(self, client: TestClient) -> None:
        resp = client.get(PROJECTS_URL, headers=_admin_h(client))
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "size" in body

    def test_list_projects_pagination(self, client: TestClient) -> None:
        resp = client.get(f"{PROJECTS_URL}?page=1&size=2", headers=_admin_h(client))
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 2
        assert body["page"] == 1
        assert body["size"] == 2

    def test_list_projects_search_by_name(self, client: TestClient) -> None:
        unique = uuid.uuid4().hex[:10]
        resp = client.post(PROJECTS_URL, json=_project_payload(name=f"SearchMe_{unique}"), headers=_admin_h(client))
        pid = resp.json()["id"]
        try:
            search = client.get(f"{PROJECTS_URL}?search={unique}", headers=_admin_h(client))
            assert search.status_code == 200
            names = [i["name"] for i in search.json()["items"]]
            assert any(unique in n for n in names)
        finally:
            _delete_project(pid)

    def test_list_projects_search_by_location(self, client: TestClient) -> None:
        unique = uuid.uuid4().hex[:10]
        resp = client.post(
            PROJECTS_URL,
            json=_project_payload(location=f"UniqueCity_{unique}"),
            headers=_admin_h(client),
        )
        pid = resp.json()["id"]
        try:
            search = client.get(f"{PROJECTS_URL}?search={unique}", headers=_admin_h(client))
            assert search.status_code == 200
            locations = [i["location"] for i in search.json()["items"]]
            assert any(unique in (loc or "") for loc in locations)
        finally:
            _delete_project(pid)

    def test_admin_can_get_project(self, client: TestClient) -> None:
        resp = client.post(PROJECTS_URL, json=_project_payload(), headers=_admin_h(client))
        pid = resp.json()["id"]
        try:
            get_resp = client.get(f"{PROJECTS_URL}/{pid}", headers=_admin_h(client))
            assert get_resp.status_code == 200
            assert get_resp.json()["id"] == pid
        finally:
            _delete_project(pid)

    def test_get_nonexistent_project_returns_404(self, client: TestClient) -> None:
        assert client.get(f"{PROJECTS_URL}/999999", headers=_admin_h(client)).status_code == 404

    def test_admin_can_update_project(self, client: TestClient) -> None:
        resp = client.post(PROJECTS_URL, json=_project_payload(), headers=_admin_h(client))
        pid = resp.json()["id"]
        try:
            upd = client.put(
                f"{PROJECTS_URL}/{pid}",
                json={"name": "Updated Name", "location": "New Location"},
                headers=_admin_h(client),
            )
            assert upd.status_code == 200
            body = upd.json()
            assert body["name"] == "Updated Name"
            assert body["location"] == "New Location"
        finally:
            _delete_project(pid)

    def test_update_nonexistent_project_returns_404(self, client: TestClient) -> None:
        resp = client.put(f"{PROJECTS_URL}/999999", json={"name": "X"}, headers=_admin_h(client))
        assert resp.status_code == 404

    def test_admin_can_delete_empty_project(self, client: TestClient) -> None:
        resp = client.post(PROJECTS_URL, json=_project_payload(), headers=_admin_h(client))
        pid = resp.json()["id"]
        del_resp = client.delete(f"{PROJECTS_URL}/{pid}", headers=_admin_h(client))
        assert del_resp.status_code == 200
        assert "deleted" in del_resp.json()["message"].lower()
        # Confirm gone
        assert client.get(f"{PROJECTS_URL}/{pid}", headers=_admin_h(client)).status_code == 404

    def test_cannot_delete_project_with_buildings(self, client: TestClient) -> None:
        # Create project → add building → try to delete project
        resp = client.post(PROJECTS_URL, json=_project_payload(), headers=_admin_h(client))
        pid = resp.json()["id"]
        b_resp = client.post(
            f"{PROJECTS_URL}/{pid}/buildings",
            json=_building_payload(),
            headers=_admin_h(client),
        )
        bid = b_resp.json()["id"]
        try:
            del_resp = client.delete(f"{PROJECTS_URL}/{pid}", headers=_admin_h(client))
            assert del_resp.status_code == 409
            assert "buildings" in del_resp.json()["detail"].lower()
        finally:
            _delete_building(bid)
            _delete_project(pid)

    def test_delete_nonexistent_project_returns_404(self, client: TestClient) -> None:
        assert client.delete(f"{PROJECTS_URL}/999999", headers=_admin_h(client)).status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# BUILDING CRUD
# ═════════════════════════════════════════════════════════════════════════════

class TestBuildingCRUD:

    def test_admin_can_create_building(self, client: TestClient, seeded_project: dict) -> None:
        resp = client.post(
            f"{PROJECTS_URL}/{seeded_project['id']}/buildings",
            json=_building_payload(),
            headers=_admin_h(client),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["project_id"] == seeded_project["id"]
        assert "id" in body
        _delete_building(body["id"])

    def test_create_building_empty_name_returns_422(self, client: TestClient, seeded_project: dict) -> None:
        resp = client.post(
            f"{PROJECTS_URL}/{seeded_project['id']}/buildings",
            json={"name": "   ", "total_floors": 5},
            headers=_admin_h(client),
        )
        assert resp.status_code == 422

    def test_create_building_invalid_total_floors_returns_422(self, client: TestClient, seeded_project: dict) -> None:
        resp = client.post(
            f"{PROJECTS_URL}/{seeded_project['id']}/buildings",
            json={"name": "Bad Building", "total_floors": 0},
            headers=_admin_h(client),
        )
        assert resp.status_code == 422

    def test_create_building_nonexistent_project_returns_404(self, client: TestClient) -> None:
        resp = client.post(
            f"{PROJECTS_URL}/999999/buildings",
            json=_building_payload(),
            headers=_admin_h(client),
        )
        assert resp.status_code == 404

    def test_admin_can_list_buildings_for_project(self, client: TestClient, seeded_project: dict) -> None:
        resp = client.get(
            f"{PROJECTS_URL}/{seeded_project['id']}/buildings",
            headers=_admin_h(client),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body

    def test_list_buildings_only_returns_project_buildings(self, client: TestClient) -> None:
        # Create two projects each with one building
        p1 = client.post(PROJECTS_URL, json=_project_payload(), headers=_admin_h(client)).json()
        p2 = client.post(PROJECTS_URL, json=_project_payload(), headers=_admin_h(client)).json()
        b1 = client.post(
            f"{PROJECTS_URL}/{p1['id']}/buildings", json=_building_payload(), headers=_admin_h(client)
        ).json()
        b2 = client.post(
            f"{PROJECTS_URL}/{p2['id']}/buildings", json=_building_payload(), headers=_admin_h(client)
        ).json()
        try:
            resp = client.get(f"{PROJECTS_URL}/{p1['id']}/buildings", headers=_admin_h(client))
            ids = [i["id"] for i in resp.json()["items"]]
            assert b1["id"] in ids
            assert b2["id"] not in ids
        finally:
            _delete_building(b1["id"])
            _delete_building(b2["id"])
            _delete_project(p1["id"])
            _delete_project(p2["id"])

    def test_list_buildings_nonexistent_project_returns_404(self, client: TestClient) -> None:
        assert client.get(f"{PROJECTS_URL}/999999/buildings", headers=_admin_h(client)).status_code == 404

    def test_admin_can_get_building(self, client: TestClient, seeded_building: dict) -> None:
        resp = client.get(f"{BUILDINGS_URL}/{seeded_building['id']}", headers=_admin_h(client))
        assert resp.status_code == 200
        assert resp.json()["id"] == seeded_building["id"]

    def test_get_nonexistent_building_returns_404(self, client: TestClient) -> None:
        assert client.get(f"{BUILDINGS_URL}/999999", headers=_admin_h(client)).status_code == 404

    def test_admin_can_update_building(self, client: TestClient, seeded_project: dict) -> None:
        b = client.post(
            f"{PROJECTS_URL}/{seeded_project['id']}/buildings",
            json=_building_payload(),
            headers=_admin_h(client),
        ).json()
        try:
            upd = client.put(
                f"{BUILDINGS_URL}/{b['id']}",
                json={"name": "Renamed Tower", "total_floors": 15},
                headers=_admin_h(client),
            )
            assert upd.status_code == 200
            body = upd.json()
            assert body["name"] == "Renamed Tower"
            assert body["total_floors"] == 15
            # project_id must not change
            assert body["project_id"] == seeded_project["id"]
        finally:
            _delete_building(b["id"])

    def test_update_nonexistent_building_returns_404(self, client: TestClient) -> None:
        assert client.put(f"{BUILDINGS_URL}/999999", json={"name": "X"}, headers=_admin_h(client)).status_code == 404

    def test_admin_can_delete_empty_building(self, client: TestClient, seeded_project: dict) -> None:
        b = client.post(
            f"{PROJECTS_URL}/{seeded_project['id']}/buildings",
            json=_building_payload(),
            headers=_admin_h(client),
        ).json()
        del_resp = client.delete(f"{BUILDINGS_URL}/{b['id']}", headers=_admin_h(client))
        assert del_resp.status_code == 200
        assert "deleted" in del_resp.json()["message"].lower()
        assert client.get(f"{BUILDINGS_URL}/{b['id']}", headers=_admin_h(client)).status_code == 404

    def test_cannot_delete_building_with_units(self, client: TestClient, seeded_project: dict) -> None:
        b = client.post(
            f"{PROJECTS_URL}/{seeded_project['id']}/buildings",
            json=_building_payload(),
            headers=_admin_h(client),
        ).json()
        u = client.post(
            f"{BUILDINGS_URL}/{b['id']}/units",
            json=_unit_payload(),
            headers=_admin_h(client),
        ).json()
        try:
            del_resp = client.delete(f"{BUILDINGS_URL}/{b['id']}", headers=_admin_h(client))
            assert del_resp.status_code == 409
            assert "units" in del_resp.json()["detail"].lower()
        finally:
            _delete_unit(u["id"])
            _delete_building(b["id"])

    def test_delete_nonexistent_building_returns_404(self, client: TestClient) -> None:
        assert client.delete(f"{BUILDINGS_URL}/999999", headers=_admin_h(client)).status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# UNIT CRUD
# ═════════════════════════════════════════════════════════════════════════════

class TestUnitCRUD:

    def test_admin_can_create_unit(self, client: TestClient, seeded_building: dict) -> None:
        payload = _unit_payload()
        resp = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=payload,
            headers=_admin_h(client),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["building_id"] == seeded_building["id"]
        assert body["unit_number"] == payload["unit_number"]
        assert body["type"] == "2BHK"
        assert body["status"] == "AVAILABLE"
        _delete_unit(body["id"])

    def test_create_unit_default_status_is_available(self, client: TestClient, seeded_building: dict) -> None:
        payload = _unit_payload()
        payload.pop("status")
        resp = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=payload,
            headers=_admin_h(client),
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "AVAILABLE"
        _delete_unit(resp.json()["id"])

    def test_create_unit_nonexistent_building_returns_404(self, client: TestClient) -> None:
        resp = client.post(
            f"{BUILDINGS_URL}/999999/units",
            json=_unit_payload(),
            headers=_admin_h(client),
        )
        assert resp.status_code == 404

    def test_create_unit_invalid_type_returns_422(self, client: TestClient, seeded_building: dict) -> None:
        payload = _unit_payload(type="STUDIO")
        resp = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=payload,
            headers=_admin_h(client),
        )
        assert resp.status_code == 422

    def test_create_unit_invalid_status_returns_422(self, client: TestClient, seeded_building: dict) -> None:
        payload = _unit_payload(status="PENDING")
        resp = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=payload,
            headers=_admin_h(client),
        )
        assert resp.status_code == 422

    def test_create_unit_negative_price_returns_422(self, client: TestClient, seeded_building: dict) -> None:
        payload = _unit_payload(price=-1000)
        resp = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=payload,
            headers=_admin_h(client),
        )
        assert resp.status_code == 422

    def test_create_unit_empty_unit_number_returns_422(self, client: TestClient, seeded_building: dict) -> None:
        payload = _unit_payload(unit_number="   ")
        resp = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=payload,
            headers=_admin_h(client),
        )
        assert resp.status_code == 422

    def test_duplicate_unit_number_same_building_returns_409(self, client: TestClient, seeded_building: dict) -> None:
        number = f"DUP-{uuid.uuid4().hex[:4].upper()}"
        r1 = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(unit_number=number),
            headers=_admin_h(client),
        )
        assert r1.status_code == 201
        try:
            r2 = client.post(
                f"{BUILDINGS_URL}/{seeded_building['id']}/units",
                json=_unit_payload(unit_number=number),
                headers=_admin_h(client),
            )
            assert r2.status_code == 409
            assert "already exists" in r2.json()["detail"].lower()
        finally:
            _delete_unit(r1.json()["id"])

    def test_same_unit_number_different_buildings_is_allowed(
        self, client: TestClient, seeded_project: dict
    ) -> None:
        number = f"SAME-{uuid.uuid4().hex[:4].upper()}"
        b1 = client.post(
            f"{PROJECTS_URL}/{seeded_project['id']}/buildings",
            json=_building_payload(),
            headers=_admin_h(client),
        ).json()
        b2 = client.post(
            f"{PROJECTS_URL}/{seeded_project['id']}/buildings",
            json=_building_payload(),
            headers=_admin_h(client),
        ).json()
        u1_id = u2_id = None
        try:
            r1 = client.post(
                f"{BUILDINGS_URL}/{b1['id']}/units",
                json=_unit_payload(unit_number=number),
                headers=_admin_h(client),
            )
            r2 = client.post(
                f"{BUILDINGS_URL}/{b2['id']}/units",
                json=_unit_payload(unit_number=number),
                headers=_admin_h(client),
            )
            assert r1.status_code == 201
            assert r2.status_code == 201
            u1_id = r1.json()["id"]
            u2_id = r2.json()["id"]
        finally:
            if u1_id:
                _delete_unit(u1_id)
            if u2_id:
                _delete_unit(u2_id)
            _delete_building(b1["id"])
            _delete_building(b2["id"])

    def test_admin_can_list_units(self, client: TestClient, seeded_building: dict) -> None:
        u = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(),
            headers=_admin_h(client),
        ).json()
        try:
            resp = client.get(f"{BUILDINGS_URL}/{seeded_building['id']}/units", headers=_admin_h(client))
            assert resp.status_code == 200
            body = resp.json()
            assert "items" in body
            assert "total" in body
            assert "page" in body
            assert "size" in body
        finally:
            _delete_unit(u["id"])

    def test_list_units_status_filter(self, client: TestClient, seeded_building: dict) -> None:
        u = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(status="AVAILABLE"),
            headers=_admin_h(client),
        ).json()
        try:
            resp = client.get(
                f"{BUILDINGS_URL}/{seeded_building['id']}/units?status=AVAILABLE",
                headers=_admin_h(client),
            )
            assert resp.status_code == 200
            statuses = [i["status"] for i in resp.json()["items"]]
            assert all(s == "AVAILABLE" for s in statuses)

            booked_resp = client.get(
                f"{BUILDINGS_URL}/{seeded_building['id']}/units?status=BOOKED",
                headers=_admin_h(client),
            )
            assert booked_resp.status_code == 200
            assert all(i["status"] == "BOOKED" for i in booked_resp.json()["items"])
        finally:
            _delete_unit(u["id"])

    def test_list_units_type_filter(self, client: TestClient, seeded_building: dict) -> None:
        u = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(type="3BHK"),
            headers=_admin_h(client),
        ).json()
        try:
            resp = client.get(
                f"{BUILDINGS_URL}/{seeded_building['id']}/units?type=3BHK",
                headers=_admin_h(client),
            )
            assert resp.status_code == 200
            types = [i["type"] for i in resp.json()["items"]]
            assert all(t == "3BHK" for t in types)
        finally:
            _delete_unit(u["id"])

    def test_list_units_pagination(self, client: TestClient, seeded_building: dict) -> None:
        resp = client.get(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units?page=1&size=2",
            headers=_admin_h(client),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 2
        assert body["page"] == 1

    def test_list_units_nonexistent_building_returns_404(self, client: TestClient) -> None:
        assert client.get(f"{BUILDINGS_URL}/999999/units", headers=_admin_h(client)).status_code == 404

    def test_admin_can_get_unit(self, client: TestClient, seeded_building: dict) -> None:
        u = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(),
            headers=_admin_h(client),
        ).json()
        try:
            resp = client.get(f"{UNITS_URL}/{u['id']}", headers=_admin_h(client))
            assert resp.status_code == 200
            assert resp.json()["id"] == u["id"]
        finally:
            _delete_unit(u["id"])

    def test_sales_can_get_unit(self, client: TestClient, seeded_building: dict) -> None:
        u = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(),
            headers=_admin_h(client),
        ).json()
        try:
            resp = client.get(f"{UNITS_URL}/{u['id']}", headers=_sales_h(client))
            assert resp.status_code == 200
        finally:
            _delete_unit(u["id"])

    def test_get_nonexistent_unit_returns_404(self, client: TestClient) -> None:
        assert client.get(f"{UNITS_URL}/999999", headers=_admin_h(client)).status_code == 404

    def test_admin_can_update_unit(self, client: TestClient, seeded_building: dict) -> None:
        u = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(type="2BHK", price=5000000),
            headers=_admin_h(client),
        ).json()
        try:
            upd = client.put(
                f"{UNITS_URL}/{u['id']}",
                json={"price": 5500000, "type": "3BHK", "status": "BOOKED"},
                headers=_admin_h(client),
            )
            assert upd.status_code == 200
            body = upd.json()
            assert float(body["price"]) == 5500000.0
            assert body["type"] == "3BHK"
            assert body["status"] == "BOOKED"
            # building_id must not change
            assert body["building_id"] == seeded_building["id"]
        finally:
            _delete_unit(u["id"])

    def test_sales_cannot_update_unit(self, client: TestClient, seeded_building: dict) -> None:
        u = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(),
            headers=_admin_h(client),
        ).json()
        try:
            resp = client.put(
                f"{UNITS_URL}/{u['id']}",
                json={"status": "BOOKED"},
                headers=_sales_h(client),
            )
            assert resp.status_code == 403
        finally:
            _delete_unit(u["id"])

    def test_update_unit_duplicate_number_returns_409(self, client: TestClient, seeded_building: dict) -> None:
        u1 = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(unit_number="AAA-001"),
            headers=_admin_h(client),
        ).json()
        u2 = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(unit_number="AAA-002"),
            headers=_admin_h(client),
        ).json()
        try:
            # Rename u2 to u1's number — should 409
            resp = client.put(
                f"{UNITS_URL}/{u2['id']}",
                json={"unit_number": "AAA-001"},
                headers=_admin_h(client),
            )
            assert resp.status_code == 409
        finally:
            _delete_unit(u1["id"])
            _delete_unit(u2["id"])

    def test_update_nonexistent_unit_returns_404(self, client: TestClient) -> None:
        assert client.put(f"{UNITS_URL}/999999", json={"status": "BOOKED"}, headers=_admin_h(client)).status_code == 404

    def test_admin_can_delete_unit_without_bookings(self, client: TestClient, seeded_building: dict) -> None:
        u = client.post(
            f"{BUILDINGS_URL}/{seeded_building['id']}/units",
            json=_unit_payload(),
            headers=_admin_h(client),
        ).json()
        del_resp = client.delete(f"{UNITS_URL}/{u['id']}", headers=_admin_h(client))
        assert del_resp.status_code == 200
        assert "deleted" in del_resp.json()["message"].lower()
        assert client.get(f"{UNITS_URL}/{u['id']}", headers=_admin_h(client)).status_code == 404

    def test_cannot_delete_unit_with_booking_history(self, client: TestClient) -> None:
        """
        The seed data includes unit A-102 (BOOKED) and a confirmed booking for it.
        We retrieve that unit by looking it up from the seed data and attempt deletion.
        """
        from src.repository.models.unit import Unit as UnitModel
        from src.repository.models.booking import Booking as BookingModel
        db = SessionLocal()
        try:
            # Find a unit that has at least one booking
            booked_unit = db.execute(
                select(UnitModel)
                .join(BookingModel, BookingModel.unit_id == UnitModel.id)
                .limit(1)
            ).scalar_one_or_none()
            if booked_unit is None:
                pytest.skip("No units with bookings found in seed data.")
            unit_id = booked_unit.id
        finally:
            db.close()

        resp = client.delete(f"{UNITS_URL}/{unit_id}", headers=_admin_h(client))
        assert resp.status_code == 409
        assert "booking" in resp.json()["detail"].lower()

    def test_delete_nonexistent_unit_returns_404(self, client: TestClient) -> None:
        assert client.delete(f"{UNITS_URL}/999999", headers=_admin_h(client)).status_code == 404
