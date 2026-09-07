"""
Database seed script — creates demo data for development and evaluation.

Run from the backend/ directory after `alembic upgrade head`:
    .venv/Scripts/python.exe -m src.migration.seed

Safety: all inserts are idempotent — running twice will not create duplicates.
Existing records (matched by email / name+building) are left unchanged.

Seed contents:
  Users      : 1 Admin, 1 Sales employee
  Projects   : 2 projects (ABC Residency, Greenfield Heights)
  Buildings  : 3 buildings across 2 projects
  Units      : 10 units (mix of types, some AVAILABLE, some BOOKED)
  Leads      : 6 leads in various stages
  FollowUps  : 3 follow-ups (PENDING, COMPLETED)
  Bookings   : 1 CONFIRMED booking, 1 CANCELLED booking
"""
import sys
import os
from datetime import datetime, timezone, timedelta

# Ensure backend/ is on the path when run as a module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.repository.database import SessionLocal
from src.repository.models.user import User
from src.repository.models.lead import Lead
from src.repository.models.lead_note import LeadNote
from src.repository.models.follow_up import FollowUp
from src.repository.models.project import Project
from src.repository.models.building import Building
from src.repository.models.unit import Unit
from src.repository.models.booking import Booking
from src.utils.enums import (
    UserRole,
    LeadStage,
    LeadSource,
    UnitType,
    UnitStatus,
    BookingStatus,
    FollowUpStatus,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def get_or_create_user(db: Session, email: str, **kwargs) -> User:
    """Return existing user or create a new one. Idempotent."""
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user:
        print(f"  [skip] User already exists: {email}")
        return user
    user = User(email=email, **kwargs)
    db.add(user)
    db.flush()
    print(f"  [create] User: {email} ({user.role})")
    return user


def get_or_create_project(db: Session, name: str, **kwargs) -> Project:
    proj = db.execute(select(Project).where(Project.name == name)).scalar_one_or_none()
    if proj:
        print(f"  [skip] Project already exists: {name}")
        return proj
    proj = Project(name=name, **kwargs)
    db.add(proj)
    db.flush()
    print(f"  [create] Project: {name}")
    return proj


def get_or_create_building(db: Session, project_id: int, name: str, **kwargs) -> Building:
    building = db.execute(
        select(Building).where(Building.project_id == project_id, Building.name == name)
    ).scalar_one_or_none()
    if building:
        print(f"  [skip] Building already exists: {name}")
        return building
    building = Building(project_id=project_id, name=name, **kwargs)
    db.add(building)
    db.flush()
    print(f"  [create] Building: {name}")
    return building


def get_or_create_unit(
    db: Session, building_id: int, unit_number: str, **kwargs
) -> Unit:
    unit = db.execute(
        select(Unit).where(Unit.building_id == building_id, Unit.unit_number == unit_number)
    ).scalar_one_or_none()
    if unit:
        print(f"  [skip] Unit already exists: {unit_number}")
        return unit
    unit = Unit(building_id=building_id, unit_number=unit_number, **kwargs)
    db.add(unit)
    db.flush()
    print(f"  [create] Unit: {unit_number} ({kwargs.get('type', '')})")
    return unit


def get_or_create_lead(db: Session, email: str, **kwargs) -> Lead:
    lead = db.execute(select(Lead).where(Lead.email == email)).scalar_one_or_none()
    if lead:
        print(f"  [skip] Lead already exists: {email}")
        return lead
    lead = Lead(email=email, **kwargs)
    db.add(lead)
    db.flush()
    print(f"  [create] Lead: {kwargs.get('name', email)} (stage={kwargs.get('stage', 'NEW')})")
    return lead


def seed() -> None:
    print("\n=== Real Estate CRM — Seed Script ===\n")

    db: Session = SessionLocal()
    try:
        # ── Users ─────────────────────────────────────────────────────────────
        print("--- Users ---")
        admin = get_or_create_user(
            db,
            email="admin@example.com",
            name="Admin User",
            password_hash=hash_password("Admin@123"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        sales = get_or_create_user(
            db,
            email="sales@example.com",
            name="Sales Employee",
            password_hash=hash_password("Sales@123"),
            role=UserRole.SALES,
            is_active=True,
        )

        # ── Projects ──────────────────────────────────────────────────────────
        print("\n--- Projects ---")
        project_abc = get_or_create_project(
            db,
            name="ABC Residency",
            location="Bandra West, Mumbai",
            description="Premium residential project with 2BHK and 3BHK apartments.",
        )
        project_green = get_or_create_project(
            db,
            name="Greenfield Heights",
            location="Whitefield, Bangalore",
            description="Luxury gated community with villas and plots.",
        )

        # ── Buildings ─────────────────────────────────────────────────────────
        print("\n--- Buildings ---")
        tower_a = get_or_create_building(
            db, project_abc.id, "Tower A", total_floors=10
        )
        tower_b = get_or_create_building(
            db, project_abc.id, "Tower B", total_floors=8
        )
        block_1 = get_or_create_building(
            db, project_green.id, "Block 1", total_floors=2
        )

        # ── Units ─────────────────────────────────────────────────────────────
        print("\n--- Units ---")
        # Tower A units
        u_a101 = get_or_create_unit(
            db, tower_a.id, "A-101",
            type=UnitType.TWO_BHK, floor=1,
            price=4500000, status=UnitStatus.AVAILABLE,
        )
        u_a102 = get_or_create_unit(
            db, tower_a.id, "A-102",
            type=UnitType.TWO_BHK, floor=1,
            price=4600000, status=UnitStatus.BOOKED,
        )
        u_a201 = get_or_create_unit(
            db, tower_a.id, "A-201",
            type=UnitType.THREE_BHK, floor=2,
            price=6500000, status=UnitStatus.AVAILABLE,
        )
        u_a202 = get_or_create_unit(
            db, tower_a.id, "A-202",
            type=UnitType.THREE_BHK, floor=2,
            price=6700000, status=UnitStatus.AVAILABLE,
        )
        # Tower B units
        u_b101 = get_or_create_unit(
            db, tower_b.id, "B-101",
            type=UnitType.TWO_BHK, floor=1,
            price=4200000, status=UnitStatus.AVAILABLE,
        )
        u_b102 = get_or_create_unit(
            db, tower_b.id, "B-102",
            type=UnitType.ONE_BHK, floor=1,
            price=2800000, status=UnitStatus.AVAILABLE,
        )
        # Block 1 units (Greenfield)
        u_g101 = get_or_create_unit(
            db, block_1.id, "G-V01",
            type=UnitType.VILLA, floor=1,
            price=12500000, status=UnitStatus.AVAILABLE,
        )
        u_g102 = get_or_create_unit(
            db, block_1.id, "G-P01",
            type=UnitType.PLOT, floor=0,
            price=3500000, status=UnitStatus.AVAILABLE,
        )
        u_g103 = get_or_create_unit(
            db, block_1.id, "G-P02",
            type=UnitType.PLOT, floor=0,
            price=3600000, status=UnitStatus.AVAILABLE,
        )
        u_g104 = get_or_create_unit(
            db, block_1.id, "G-V02",
            type=UnitType.VILLA, floor=1,
            price=13000000, status=UnitStatus.BOOKED,
        )

        # ── Leads ─────────────────────────────────────────────────────────────
        print("\n--- Leads ---")
        now = datetime.now(timezone.utc)

        lead_rahul = get_or_create_lead(
            db, "rahul@example.com",
            name="Rahul Kumar",
            phone="9876543210",
            source=LeadSource.WEBSITE,
            stage=LeadStage.BOOKED,
            assigned_to=sales.id,
            is_active=True,
        )
        lead_priya = get_or_create_lead(
            db, "priya@example.com",
            name="Priya Sharma",
            phone="9876543211",
            source=LeadSource.REFERRAL,
            stage=LeadStage.NEGOTIATION,
            assigned_to=sales.id,
            is_active=True,
        )
        lead_arjun = get_or_create_lead(
            db, "arjun@example.com",
            name="Arjun Mehta",
            phone="9876543212",
            source=LeadSource.ADVERTISEMENT,
            stage=LeadStage.INTERESTED,
            assigned_to=sales.id,
            is_active=True,
        )
        lead_sunita = get_or_create_lead(
            db, "sunita@example.com",
            name="Sunita Verma",
            phone="9876543213",
            source=LeadSource.WALK_IN,
            stage=LeadStage.SITE_VISIT,
            assigned_to=admin.id,
            is_active=True,
        )
        lead_vikram = get_or_create_lead(
            db, "vikram@example.com",
            name="Vikram Singh",
            phone="9876543214",
            source=LeadSource.SOCIAL_MEDIA,
            stage=LeadStage.CONTACTED,
            assigned_to=sales.id,
            is_active=True,
        )
        lead_neha = get_or_create_lead(
            db, "neha@example.com",
            name="Neha Gupta",
            phone="9876543215",
            source=LeadSource.WEBSITE,
            stage=LeadStage.NEW,
            assigned_to=None,  # Unassigned lead — admin can see it
            is_active=True,
        )

        # ── Lead Notes ────────────────────────────────────────────────────────
        print("\n--- Lead Notes ---")
        # Only add notes if none exist for this lead
        if not db.execute(
            select(LeadNote).where(LeadNote.lead_id == lead_priya.id)
        ).scalar_one_or_none():
            db.add(LeadNote(
                lead_id=lead_priya.id,
                user_id=sales.id,
                note="Customer is interested in a 3BHK in Tower A. Budget around 65-70L.",
            ))
            db.add(LeadNote(
                lead_id=lead_priya.id,
                user_id=sales.id,
                note="Revisited site on Saturday. Very happy with A-201. Negotiating price.",
            ))
            print("  [create] Notes for Priya Sharma")
        else:
            print("  [skip] Notes for Priya Sharma already exist")

        if not db.execute(
            select(LeadNote).where(LeadNote.lead_id == lead_arjun.id)
        ).scalar_one_or_none():
            db.add(LeadNote(
                lead_id=lead_arjun.id,
                user_id=sales.id,
                note="Interested in 2BHK. Prefers lower floor. Showed A-101 and B-101.",
            ))
            print("  [create] Note for Arjun Mehta")
        else:
            print("  [skip] Note for Arjun Mehta already exists")

        db.flush()

        # ── Follow-Ups ────────────────────────────────────────────────────────
        print("\n--- Follow-Ups ---")
        if not db.execute(
            select(FollowUp).where(FollowUp.lead_id == lead_priya.id)
        ).scalar_one_or_none():
            db.add(FollowUp(
                lead_id=lead_priya.id,
                assigned_to=sales.id,
                follow_up_at=now + timedelta(days=2),
                notes="Call to discuss final price for A-201.",
                status=FollowUpStatus.PENDING,
            ))
            print("  [create] Follow-up: Priya Sharma (PENDING)")
        else:
            print("  [skip] Follow-up for Priya already exists")

        if not db.execute(
            select(FollowUp).where(FollowUp.lead_id == lead_arjun.id)
        ).scalar_one_or_none():
            db.add(FollowUp(
                lead_id=lead_arjun.id,
                assigned_to=sales.id,
                follow_up_at=now + timedelta(days=1),
                notes="Send brochure and floor plan for B-101.",
                status=FollowUpStatus.PENDING,
            ))
            print("  [create] Follow-up: Arjun Mehta (PENDING)")
        else:
            print("  [skip] Follow-up for Arjun already exists")

        if not db.execute(
            select(FollowUp).where(FollowUp.lead_id == lead_vikram.id)
        ).scalar_one_or_none():
            db.add(FollowUp(
                lead_id=lead_vikram.id,
                assigned_to=sales.id,
                follow_up_at=now - timedelta(days=3),
                notes="Called customer. Site visit scheduled for next week.",
                status=FollowUpStatus.COMPLETED,
            ))
            print("  [create] Follow-up: Vikram Singh (COMPLETED)")
        else:
            print("  [skip] Follow-up for Vikram already exists")

        db.flush()

        # ── Bookings ──────────────────────────────────────────────────────────
        print("\n--- Bookings ---")
        # CONFIRMED booking: Rahul → A-102 (unit is BOOKED)
        confirmed = db.execute(
            select(Booking).where(
                Booking.lead_id == lead_rahul.id,
                Booking.unit_id == u_a102.id,
                Booking.status == BookingStatus.CONFIRMED,
            )
        ).scalar_one_or_none()
        if not confirmed:
            db.add(Booking(
                lead_id=lead_rahul.id,
                unit_id=u_a102.id,
                booked_by=sales.id,
                amount=4600000,
                status=BookingStatus.CONFIRMED,
                # booking_date uses server default (NOW()) — not set here
            ))
            print("  [create] CONFIRMED booking: Rahul → A-102")
        else:
            print("  [skip] CONFIRMED booking for Rahul already exists")

        # CANCELLED booking: historical — G-V02 was booked then cancelled
        # Note: G-V02 is still BOOKED in units (a separate new booking made later)
        cancelled = db.execute(
            select(Booking).where(
                Booking.unit_id == u_g104.id,
                Booking.status == BookingStatus.CANCELLED,
            )
        ).scalar_one_or_none()
        if not cancelled:
            db.add(Booking(
                lead_id=lead_sunita.id,
                unit_id=u_g104.id,
                booked_by=admin.id,
                amount=13000000,
                status=BookingStatus.CANCELLED,
            ))
            print("  [create] CANCELLED booking: Sunita → G-V02")
        else:
            print("  [skip] CANCELLED booking for Sunita already exists")

        # G-V02 is BOOKED — add the CONFIRMED booking for it (different lead)
        # This tests that CANCELLED + CONFIRMED can coexist for the same unit
        confirmed_gv02 = db.execute(
            select(Booking).where(
                Booking.unit_id == u_g104.id,
                Booking.status == BookingStatus.CONFIRMED,
            )
        ).scalar_one_or_none()
        if not confirmed_gv02:
            db.add(Booking(
                lead_id=lead_arjun.id,
                unit_id=u_g104.id,
                booked_by=admin.id,
                amount=13000000,
                status=BookingStatus.CONFIRMED,
            ))
            print("  [create] CONFIRMED booking: Arjun → G-V02 (demonstrates CANCELLED+CONFIRMED coexist)")
        else:
            print("  [skip] CONFIRMED booking for G-V02 already exists")

        # ── Commit all ────────────────────────────────────────────────────────
        db.commit()
        print("\n=== Seed complete. ===")
        print("\nDemo credentials:")
        print("  Admin : admin@example.com  / Admin@123")
        print("  Sales : sales@example.com  / Sales@123")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
