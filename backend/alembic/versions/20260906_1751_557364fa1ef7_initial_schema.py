"""initial_schema

Revision ID: 557364fa1ef7
Revises:
Create Date: 2026-09-06 17:51:54.365777+00:00

Creates all 8 CRM tables with:
  - All enum types
  - All FK constraints with correct ON DELETE behavior
  - All performance indexes
  - UNIQUE(building_id, unit_number) on units
  - MANDATORY partial unique index: uix_unit_confirmed_booking
    ON bookings(unit_id) WHERE status = 'CONFIRMED'
    This is the database-level guard against duplicate confirmed bookings.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "557364fa1ef7"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types (created before tables that use them) ─────────────────────
    # Note: Alembic creates these automatically via sa.Enum(name=...) in
    # create_table calls below. Listed here for documentation clarity.

    # ── projects ──────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "SALES", name="user_role"),
            nullable=False,
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # UNIQUE + index on email for fast login lookups
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # ── buildings ─────────────────────────────────────────────────────────────
    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("total_floors", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # ON DELETE RESTRICT: cannot delete project with buildings
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_buildings_project_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_buildings_project_id"), "buildings", ["project_id"], unique=False
    )

    # ── leads ─────────────────────────────────────────────────────────────────
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column(
            "source",
            sa.Enum(
                "WEBSITE",
                "REFERRAL",
                "ADVERTISEMENT",
                "WALK_IN",
                "SOCIAL_MEDIA",
                "OTHER",
                name="lead_source",
            ),
            nullable=True,
        ),
        sa.Column(
            "stage",
            sa.Enum(
                "NEW",
                "CONTACTED",
                "SITE_VISIT",
                "INTERESTED",
                "NEGOTIATION",
                "BOOKED",
                "LOST",
                name="lead_stage",
            ),
            server_default="NEW",
            nullable=False,
        ),
        # NULLABLE — lead may be unassigned
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # ON DELETE SET NULL: if user deleted, lead becomes unassigned
        sa.ForeignKeyConstraint(
            ["assigned_to"],
            ["users.id"],
            name="fk_leads_assigned_to",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_leads_assigned_to", "leads", ["assigned_to"], unique=False)
    op.create_index("idx_leads_is_active", "leads", ["is_active"], unique=False)
    op.create_index("idx_leads_stage", "leads", ["stage"], unique=False)

    # ── follow_ups ────────────────────────────────────────────────────────────
    op.create_table(
        "follow_ups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("assigned_to", sa.Integer(), nullable=False),
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "COMPLETED", "CANCELLED", name="follow_up_status"),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # ON DELETE CASCADE: delete lead → delete its follow-ups
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["leads.id"],
            name="fk_follow_ups_lead_id",
            ondelete="CASCADE",
        ),
        # ON DELETE RESTRICT: cannot delete user with follow-ups
        sa.ForeignKeyConstraint(
            ["assigned_to"],
            ["users.id"],
            name="fk_follow_ups_assigned_to",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Composite index for dashboard upcoming-follow-ups queries
    op.create_index(
        "idx_followups_assignee_status",
        "follow_ups",
        ["assigned_to", "status", "follow_up_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_follow_ups_assigned_to"), "follow_ups", ["assigned_to"], unique=False
    )
    op.create_index(
        op.f("ix_follow_ups_lead_id"), "follow_ups", ["lead_id"], unique=False
    )

    # ── lead_notes ────────────────────────────────────────────────────────────
    op.create_table(
        "lead_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        # No updated_at — notes are IMMUTABLE / APPEND-ONLY
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # ON DELETE CASCADE: delete lead → delete its notes
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["leads.id"],
            name="fk_lead_notes_lead_id",
            ondelete="CASCADE",
        ),
        # ON DELETE RESTRICT: cannot delete user who has notes
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_lead_notes_user_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_lead_notes_lead_id"), "lead_notes", ["lead_id"], unique=False
    )
    op.create_index(
        op.f("ix_lead_notes_user_id"), "lead_notes", ["user_id"], unique=False
    )

    # ── units ─────────────────────────────────────────────────────────────────
    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("building_id", sa.Integer(), nullable=False),
        sa.Column("unit_number", sa.String(length=50), nullable=False),
        sa.Column(
            "type",
            # SD-required values: 1BHK, 2BHK, 3BHK, 4BHK, VILLA, PLOT
            sa.Enum("1BHK", "2BHK", "3BHK", "4BHK", "VILLA", "PLOT", name="unit_type"),
            nullable=False,
        ),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "status",
            sa.Enum("AVAILABLE", "BOOKED", name="unit_status"),
            server_default="AVAILABLE",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # ON DELETE RESTRICT: cannot delete building with units
        sa.ForeignKeyConstraint(
            ["building_id"],
            ["buildings.id"],
            name="fk_units_building_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        # CRITICAL: no duplicate unit numbers within a building
        sa.UniqueConstraint(
            "building_id", "unit_number", name="uix_building_unit_number"
        ),
    )
    op.create_index(
        "idx_units_building_status", "units", ["building_id", "status"], unique=False
    )
    op.create_index("idx_units_status", "units", ["status"], unique=False)

    # ── bookings ──────────────────────────────────────────────────────────────
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("booked_by", sa.Integer(), nullable=False),
        # booking_date is ALWAYS server-generated — never client-supplied
        sa.Column(
            "booking_date",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # amount is OPTIONAL; if supplied must be >= 0 (enforced in service layer)
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column(
            "status",
            sa.Enum("CONFIRMED", "CANCELLED", name="booking_status"),
            server_default="CONFIRMED",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # ON DELETE RESTRICT on all three FKs
        sa.ForeignKeyConstraint(
            ["lead_id"],
            ["leads.id"],
            name="fk_bookings_lead_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["units.id"],
            name="fk_bookings_unit_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["booked_by"],
            ["users.id"],
            name="fk_bookings_booked_by",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_bookings_booked_by", "bookings", ["booked_by"], unique=False)
    op.create_index("idx_bookings_lead_id", "bookings", ["lead_id"], unique=False)
    op.create_index("idx_bookings_status", "bookings", ["status"], unique=False)

    # ── MANDATORY PARTIAL UNIQUE INDEX ────────────────────────────────────────
    # Guarantees only ONE CONFIRMED booking can exist per unit.
    # This is the database-level backstop for the booking concurrency strategy.
    # CANCELLED bookings are excluded — a unit can be re-booked after cancellation.
    #
    # Cannot be expressed in SQLAlchemy __table_args__; must be explicit SQL here.
    op.execute(
        """
        CREATE UNIQUE INDEX uix_unit_confirmed_booking
        ON bookings (unit_id)
        WHERE status = 'CONFIRMED'
        """
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    # Drop partial unique index first (before dropping bookings table)
    op.execute("DROP INDEX IF EXISTS uix_unit_confirmed_booking")

    op.drop_index("idx_bookings_status", table_name="bookings")
    op.drop_index("idx_bookings_lead_id", table_name="bookings")
    op.drop_index("idx_bookings_booked_by", table_name="bookings")
    op.drop_table("bookings")

    op.drop_index("idx_units_status", table_name="units")
    op.drop_index("idx_units_building_status", table_name="units")
    op.drop_table("units")

    op.drop_index(op.f("ix_lead_notes_user_id"), table_name="lead_notes")
    op.drop_index(op.f("ix_lead_notes_lead_id"), table_name="lead_notes")
    op.drop_table("lead_notes")

    op.drop_index(op.f("ix_follow_ups_lead_id"), table_name="follow_ups")
    op.drop_index(op.f("ix_follow_ups_assigned_to"), table_name="follow_ups")
    op.drop_index("idx_followups_assignee_status", table_name="follow_ups")
    op.drop_table("follow_ups")

    op.drop_index("idx_leads_stage", table_name="leads")
    op.drop_index("idx_leads_is_active", table_name="leads")
    op.drop_index("idx_leads_assigned_to", table_name="leads")
    op.drop_table("leads")

    op.drop_index(op.f("ix_buildings_project_id"), table_name="buildings")
    op.drop_table("buildings")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.drop_table("projects")

    # Drop enum types
    sa.Enum(name="booking_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="unit_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="unit_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="follow_up_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="lead_stage").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="lead_source").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
