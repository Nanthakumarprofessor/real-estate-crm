"""
Phase 2 database constraint tests.

These tests run against a real PostgreSQL database to verify that all
SD-required constraints are enforced at the database level — not just
in application code.

Prerequisites:
  - PostgreSQL running and real_estate_crm database migrated:
      alembic upgrade head
  - .env configured with a valid DATABASE_URL

Test coverage:
  1.  User email UNIQUE constraint
  2.  UNIQUE(building_id, unit_number) on units
  3.  uix_unit_confirmed_booking partial unique index
  4.  CANCELLED booking does NOT conflict with partial unique index
  5.  FK ON DELETE CASCADE: lead_notes deleted when lead is deleted
  6.  FK ON DELETE CASCADE: follow_ups deleted when lead is deleted
  7.  FK ON DELETE RESTRICT: cannot delete user who has notes
  8.  FK ON DELETE SET NULL: lead.assigned_to becomes NULL when user deleted
  9.  amount constraint: negative amount is rejected (service-layer, not DB)
  10. booking_date is server-generated (not None after insert without explicit set)
  11. Seed users exist with hashed passwords
  12. Enum values stored correctly (1BHK, 2BHK etc.)
"""
import pytest
from decimal import Decimal
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.repository.database import SessionLocal
from src.repository.models.booking import Booking
from src.repository.models.building import Building
from src.repository.models.follow_up import FollowUp
from src.repository.models.lead import Lead
from src.repository.models.lead_note import LeadNote
from src.repository.models.project import Project
from src.repository.models.unit import Unit
from src.repository.models.user import User
from src.utils.enums import (
    BookingStatus,
    FollowUpStatus,
    LeadSource,
    LeadStage,
    UnitStatus,
    UnitType,
    UserRole,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db() -> Session:
    """
    Provides a database session that is rolled back after every test.
    This keeps tests isolated without destroying real data.
    Uses a SAVEPOINT so the outer transaction is never committed.
    """
    session = SessionLocal()
    session.begin_nested()  # SAVEPOINT
    yield session
    session.rollback()
    session.close()


def _make_user(db: Session, email: str, role: UserRole = UserRole.SALES) -> User:
    """Helper: create and flush a test user."""
    u = User(
        name="Test User",
        email=email,
        password_hash=pwd_context.hash("Test@123"),
        role=role,
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _make_project(db: Session, name: str = "Test Project") -> Project:
    p = Project(name=name, location="Test City")
    db.add(p)
    db.flush()
    return p


def _make_building(db: Session, project_id: int, name: str = "Block A") -> Building:
    b = Building(project_id=project_id, name=name, total_floors=5)
    db.add(b)
    db.flush()
    return b


def _make_unit(
    db: Session,
    building_id: int,
    unit_number: str = "101",
    status: UnitStatus = UnitStatus.AVAILABLE,
    unit_type: UnitType = UnitType.TWO_BHK,
) -> Unit:
    u = Unit(
        building_id=building_id,
        unit_number=unit_number,
        type=unit_type,
        floor=1,
        price=Decimal("4500000"),
        status=status,
    )
    db.add(u)
    db.flush()
    return u


def _make_lead(db: Session, email: str, assigned_to: int | None = None) -> Lead:
    lead = Lead(
        name="Test Lead",
        email=email,
        stage=LeadStage.NEW,
        source=LeadSource.WEBSITE,
        assigned_to=assigned_to,
        is_active=True,
    )
    db.add(lead)
    db.flush()
    return lead


def _make_booking(
    db: Session,
    lead_id: int,
    unit_id: int,
    booked_by: int,
    status: BookingStatus = BookingStatus.CONFIRMED,
    amount: Decimal | None = None,
) -> Booking:
    b = Booking(
        lead_id=lead_id,
        unit_id=unit_id,
        booked_by=booked_by,
        status=status,
        amount=amount,
    )
    db.add(b)
    db.flush()
    return b


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestUserEmailUnique:
    """Test 1: users.email has a UNIQUE constraint."""

    def test_duplicate_email_raises_integrity_error(self, db: Session) -> None:
        """Inserting two users with the same email must raise IntegrityError."""
        email = "unique_test@example.com"
        _make_user(db, email)

        with pytest.raises(IntegrityError, match="ix_users_email|unique"):
            _make_user(db, email)
            db.flush()

    def test_different_emails_succeed(self, db: Session) -> None:
        """Two users with different emails must both be inserted successfully."""
        _make_user(db, "user_a@test.com")
        _make_user(db, "user_b@test.com")
        db.flush()  # should not raise


class TestUnitBuildingUniqueConstraint:
    """Test 2: UNIQUE(building_id, unit_number) on units."""

    def test_duplicate_unit_number_in_same_building_raises(self, db: Session) -> None:
        """Two units with same unit_number in same building must fail."""
        project = _make_project(db)
        building = _make_building(db, project.id)

        _make_unit(db, building.id, "101")

        with pytest.raises(IntegrityError, match="uix_building_unit_number|unique"):
            _make_unit(db, building.id, "101")
            db.flush()

    def test_same_unit_number_in_different_buildings_succeeds(self, db: Session) -> None:
        """Same unit_number in different buildings must succeed."""
        project = _make_project(db)
        b1 = _make_building(db, project.id, "Building 1")
        b2 = _make_building(db, project.id, "Building 2")

        _make_unit(db, b1.id, "101")
        _make_unit(db, b2.id, "101")  # should not raise
        db.flush()


class TestBookingPartialUniqueIndex:
    """Test 3 & 4: uix_unit_confirmed_booking partial unique index."""

    def test_two_confirmed_bookings_for_same_unit_raises(self, db: Session) -> None:
        """
        CRITICAL: Two CONFIRMED bookings for the same unit must be rejected
        by the database partial unique index.
        """
        user = _make_user(db, "booker1@test.com")
        project = _make_project(db)
        building = _make_building(db, project.id)
        unit = _make_unit(db, building.id, "201", UnitStatus.AVAILABLE)

        lead1 = _make_lead(db, "customer1@test.com")
        lead2 = _make_lead(db, "customer2@test.com")

        _make_booking(db, lead1.id, unit.id, user.id, BookingStatus.CONFIRMED)

        with pytest.raises(IntegrityError, match="uix_unit_confirmed_booking|unique"):
            _make_booking(db, lead2.id, unit.id, user.id, BookingStatus.CONFIRMED)
            db.flush()

    def test_cancelled_and_confirmed_booking_for_same_unit_succeeds(
        self, db: Session
    ) -> None:
        """
        CANCELLED bookings must NOT be blocked by the partial unique index.
        A unit can have one CANCELLED + one CONFIRMED booking (re-booked after cancel).
        """
        user = _make_user(db, "booker2@test.com")
        project = _make_project(db)
        building = _make_building(db, project.id)
        unit = _make_unit(db, building.id, "301", UnitStatus.AVAILABLE)

        lead1 = _make_lead(db, "cust_old@test.com")
        lead2 = _make_lead(db, "cust_new@test.com")

        # First booking cancelled (old customer backed out)
        _make_booking(db, lead1.id, unit.id, user.id, BookingStatus.CANCELLED)

        # New confirmed booking for same unit — must succeed
        _make_booking(db, lead2.id, unit.id, user.id, BookingStatus.CONFIRMED)
        db.flush()  # must NOT raise

    def test_multiple_cancelled_bookings_for_same_unit_succeeds(
        self, db: Session
    ) -> None:
        """Multiple CANCELLED bookings for the same unit must all succeed."""
        user = _make_user(db, "booker3@test.com")
        project = _make_project(db)
        building = _make_building(db, project.id)
        unit = _make_unit(db, building.id, "401", UnitStatus.AVAILABLE)

        for i in range(3):
            lead = _make_lead(db, f"cancelled_cust_{i}@test.com")
            _make_booking(db, lead.id, unit.id, user.id, BookingStatus.CANCELLED)

        db.flush()  # must NOT raise


class TestForeignKeyOnDelete:
    """Tests 5–8: FK ON DELETE behavior."""

    def test_cascade_lead_notes_deleted_with_lead(self, db: Session) -> None:
        """Test 5: FK ON DELETE CASCADE — lead_notes.lead_id → leads."""
        user = _make_user(db, "note_user@test.com")
        lead = _make_lead(db, "noted_lead@test.com")

        note = LeadNote(lead_id=lead.id, user_id=user.id, note="Test note")
        db.add(note)
        db.flush()
        note_id = note.id

        # Physically delete the lead — notes must cascade
        db.delete(lead)
        db.flush()

        # Note should be gone
        result = db.execute(select(LeadNote).where(LeadNote.id == note_id)).scalar_one_or_none()
        assert result is None, "LeadNote should have been CASCADE deleted with its lead"

    def test_cascade_follow_ups_deleted_with_lead(self, db: Session) -> None:
        """Test 6: FK ON DELETE CASCADE — follow_ups.lead_id → leads."""
        user = _make_user(db, "fu_user@test.com")
        lead = _make_lead(db, "fu_lead@test.com")
        from datetime import datetime, timezone, timedelta

        fu = FollowUp(
            lead_id=lead.id,
            assigned_to=user.id,
            follow_up_at=datetime.now(timezone.utc) + timedelta(days=1),
            status=FollowUpStatus.PENDING,
        )
        db.add(fu)
        db.flush()
        fu_id = fu.id

        db.delete(lead)
        db.flush()

        result = db.execute(select(FollowUp).where(FollowUp.id == fu_id)).scalar_one_or_none()
        assert result is None, "FollowUp should have been CASCADE deleted with its lead"

    def test_restrict_cannot_delete_user_with_notes(self, db: Session) -> None:
        """Test 7: FK ON DELETE RESTRICT — lead_notes.user_id → users."""
        user = _make_user(db, "restricted_user@test.com")
        lead = _make_lead(db, "restrict_lead@test.com")

        note = LeadNote(lead_id=lead.id, user_id=user.id, note="Restricted note")
        db.add(note)
        db.flush()

        # Attempting to delete the user must fail
        with pytest.raises(IntegrityError, match="fk_lead_notes_user_id|foreign key|violates"):
            db.delete(user)
            db.flush()

    def test_set_null_assigned_to_when_user_deleted(self, db: Session) -> None:
        """Test 8: FK ON DELETE SET NULL — leads.assigned_to → users."""
        user = _make_user(db, "set_null_user@test.com")
        lead = _make_lead(db, "assigned_lead@test.com", assigned_to=user.id)

        assert lead.assigned_to == user.id

        db.delete(user)
        db.flush()
        db.refresh(lead)

        assert lead.assigned_to is None, "assigned_to should be NULL after user deletion"


class TestBookingAmountAndDate:
    """Tests 9–10: amount and booking_date constraints."""

    def test_booking_date_is_server_generated(self, db: Session) -> None:
        """
        Test 10: booking_date must be set by the server (DEFAULT NOW()).
        After insert (without explicitly setting booking_date), it must not be None.
        """
        user = _make_user(db, "date_user@test.com")
        project = _make_project(db)
        building = _make_building(db, project.id)
        unit = _make_unit(db, building.id, "D01")
        lead = _make_lead(db, "date_lead@test.com")

        # Do NOT set booking_date — it should be server-populated
        booking = Booking(
            lead_id=lead.id,
            unit_id=unit.id,
            booked_by=user.id,
            status=BookingStatus.CONFIRMED,
            amount=None,
            # booking_date intentionally omitted
        )
        db.add(booking)
        db.flush()
        db.refresh(booking)

        assert booking.booking_date is not None, (
            "booking_date should be server-generated via DEFAULT NOW()"
        )

    def test_booking_amount_nullable(self, db: Session) -> None:
        """Test 9a: amount may be None (nullable)."""
        user = _make_user(db, "amt_null_user@test.com")
        project = _make_project(db)
        building = _make_building(db, project.id)
        unit = _make_unit(db, building.id, "N01")
        lead = _make_lead(db, "amt_null_lead@test.com")

        booking = _make_booking(db, lead.id, unit.id, user.id, amount=None)
        db.refresh(booking)
        assert booking.amount is None

    def test_booking_amount_stores_correctly(self, db: Session) -> None:
        """Test 9b: a valid positive amount is stored correctly."""
        user = _make_user(db, "amt_pos_user@test.com")
        project = _make_project(db)
        building = _make_building(db, project.id)
        unit = _make_unit(db, building.id, "P01")
        lead = _make_lead(db, "amt_pos_lead@test.com")

        booking = _make_booking(
            db, lead.id, unit.id, user.id, amount=Decimal("4500000.00")
        )
        db.refresh(booking)
        assert booking.amount == Decimal("4500000.00")


class TestUnitTypeEnumValues:
    """Test 12: Unit type enum stores SD-required values (1BHK not ONE_BHK)."""

    def test_unit_type_values_are_sd_compliant(self, db: Session) -> None:
        """The database must store 1BHK, 2BHK, 3BHK etc. — not Python names."""
        project = _make_project(db)
        building = _make_building(db, project.id)

        types_to_test = [
            (UnitType.ONE_BHK, "1BHK"),
            (UnitType.TWO_BHK, "2BHK"),
            (UnitType.THREE_BHK, "3BHK"),
            (UnitType.FOUR_BHK, "4BHK"),
            (UnitType.VILLA, "VILLA"),
            (UnitType.PLOT, "PLOT"),
        ]

        for i, (enum_val, expected_db_value) in enumerate(types_to_test):
            unit = _make_unit(db, building.id, f"T{i:02d}", unit_type=enum_val)
            db.refresh(unit)
            # The ORM value (str enum) must equal the expected DB string
            assert unit.type.value == expected_db_value, (
                f"Expected {expected_db_value!r}, got {unit.type.value!r}"
            )


class TestSeedData:
    """Test 11: Seed users exist and passwords are properly hashed."""

    def test_admin_user_exists(self) -> None:
        """Admin user from seed must exist in the database."""
        db = SessionLocal()
        try:
            user = db.execute(
                select(User).where(User.email == "admin@example.com")
            ).scalar_one_or_none()
            assert user is not None, "admin@example.com not found — run seed first"
            assert user.role == UserRole.ADMIN
            assert user.is_active is True
            assert user.name == "Admin User"
        finally:
            db.close()

    def test_sales_user_exists(self) -> None:
        """Sales user from seed must exist in the database."""
        db = SessionLocal()
        try:
            user = db.execute(
                select(User).where(User.email == "sales@example.com")
            ).scalar_one_or_none()
            assert user is not None, "sales@example.com not found — run seed first"
            assert user.role == UserRole.SALES
            assert user.is_active is True
        finally:
            db.close()

    def test_admin_password_is_hashed_not_plaintext(self) -> None:
        """Admin password must be stored as a bcrypt hash, not plaintext."""
        db = SessionLocal()
        try:
            user = db.execute(
                select(User).where(User.email == "admin@example.com")
            ).scalar_one_or_none()
            assert user is not None, "admin@example.com not found — run seed first"
            # The stored value must NOT be the plaintext password
            assert user.password_hash != "Admin@123", "Password stored as plaintext!"
            # It must be a valid bcrypt hash
            assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$"), (
                f"Not a bcrypt hash: {user.password_hash[:20]}..."
            )
            # And it must verify correctly
            assert pwd_context.verify("Admin@123", user.password_hash), (
                "Admin@123 does not verify against stored hash"
            )
        finally:
            db.close()

    def test_sales_password_is_hashed_not_plaintext(self) -> None:
        """Sales password must be stored as a bcrypt hash, not plaintext."""
        db = SessionLocal()
        try:
            user = db.execute(
                select(User).where(User.email == "sales@example.com")
            ).scalar_one_or_none()
            assert user is not None
            assert user.password_hash != "Sales@123"
            assert pwd_context.verify("Sales@123", user.password_hash)
        finally:
            db.close()

    def test_seed_projects_exist(self) -> None:
        """At least 2 projects must exist after seeding."""
        db = SessionLocal()
        try:
            count = db.execute(select(Project)).scalars().all()
            assert len(count) >= 2, f"Expected >= 2 projects, got {len(count)}"
        finally:
            db.close()

    def test_seed_confirmed_booking_exists(self) -> None:
        """At least 1 CONFIRMED booking must exist after seeding."""
        db = SessionLocal()
        try:
            bookings = db.execute(
                select(Booking).where(Booking.status == BookingStatus.CONFIRMED)
            ).scalars().all()
            assert len(bookings) >= 1, "No CONFIRMED bookings found — run seed first"
        finally:
            db.close()

    def test_seed_cancelled_booking_exists(self) -> None:
        """At least 1 CANCELLED booking must exist after seeding."""
        db = SessionLocal()
        try:
            bookings = db.execute(
                select(Booking).where(Booking.status == BookingStatus.CANCELLED)
            ).scalars().all()
            assert len(bookings) >= 1, "No CANCELLED bookings found — run seed first"
        finally:
            db.close()
