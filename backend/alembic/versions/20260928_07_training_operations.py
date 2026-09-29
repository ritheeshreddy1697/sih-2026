"""Add training operations and logistics.

Revision ID: 20260928_07
Revises: 20260928_06
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260928_07"
down_revision: str | None = "20260928_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column[object]]:
    return [
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
    ]


def indexes(table: str, *columns: str) -> None:
    for column in columns:
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column])


def upgrade() -> None:
    op.create_table(
        "training_venues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("capacity > 0", name="ck_training_venue_capacity_positive"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_id", "name", name="uq_training_venue_institution_name"
        ),
    )
    indexes("training_venues", "institution_id")

    op.create_table(
        "classrooms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("equipment", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("capacity > 0", name="ck_classroom_capacity_positive"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["venue_id"], ["training_venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "code", name="uq_classroom_institution_code"),
        sa.UniqueConstraint("venue_id", "name", name="uq_classroom_venue_name"),
    )
    indexes("classrooms", "institution_id", "venue_id")

    op.create_table(
        "timetable_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("trainer_id", sa.Uuid(), nullable=False),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="scheduled", nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("ends_at > starts_at", name="ck_timetable_session_window"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_id"], ["programme_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trainer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["venue_id"], ["training_venues.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    indexes(
        "timetable_sessions",
        "institution_id",
        "programme_id",
        "batch_id",
        "trainer_id",
        "venue_id",
        "classroom_id",
        "starts_at",
        "ends_at",
        "status",
    )

    op.create_table(
        "hostel_buildings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "institution_id", "name", name="uq_hostel_building_institution_name"
        ),
    )
    indexes("hostel_buildings", "institution_id")

    op.create_table(
        "hostel_rooms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column("room_number", sa.String(length=64), nullable=False),
        sa.Column("floor", sa.String(length=64), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("is_accessible", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("capacity > 0", name="ck_hostel_room_capacity_positive"),
        sa.ForeignKeyConstraint(["building_id"], ["hostel_buildings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("building_id", "room_number", name="uq_hostel_room_number"),
    )
    indexes("hostel_rooms", "building_id")

    op.create_table(
        "hostel_beds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("bed_number", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["room_id"], ["hostel_rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "bed_number", name="uq_hostel_bed_number"),
    )
    indexes("hostel_beds", "room_id")

    op.create_table(
        "bed_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bed_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("allocated_by_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="reserved", nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("end_date >= start_date", name="ck_bed_allocation_window"),
        sa.ForeignKeyConstraint(["bed_id"], ["hostel_beds.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["allocated_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    indexes(
        "bed_allocations", "bed_id", "enrollment_id", "start_date", "end_date", "status"
    )

    op.create_table(
        "participant_logistics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column(
            "meal_preference",
            sa.String(length=24),
            server_default="vegetarian",
            nullable=False,
        ),
        sa.Column("dietary_notes", sa.Text(), nullable=True),
        sa.Column("arrival_mode", sa.String(length=24), nullable=True),
        sa.Column("arrival_details", sa.Text(), nullable=True),
        sa.Column("arrival_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("departure_mode", sa.String(length=24), nullable=True),
        sa.Column("departure_details", sa.Text(), nullable=True),
        sa.Column("departure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("emergency_contact_name", sa.String(length=255), nullable=False),
        sa.Column("emergency_contact_phone", sa.String(length=32), nullable=False),
        sa.Column("emergency_contact_relationship", sa.String(length=120), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", name="uq_participant_logistics_enrollment"),
    )
    indexes("participant_logistics", "enrollment_id")

    op.create_table(
        "training_materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("programme_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity_available", sa.Integer(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "quantity_available >= 0", name="ck_training_material_quantity_positive"
        ),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("programme_id", "name", name="uq_training_material_programme_name"),
    )
    indexes("training_materials", "institution_id", "programme_id")

    op.create_table(
        "material_distributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("distributed_by_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "distributed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity > 0", name="ck_material_distribution_quantity_positive"),
        sa.ForeignKeyConstraint(["material_id"], ["training_materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["distributed_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("material_id", "enrollment_id", name="uq_material_distribution"),
    )
    indexes("material_distributions", "material_id", "enrollment_id")

    op.create_table(
        "operations_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=True),
        sa.Column("reported_by_id", sa.Uuid(), nullable=False),
        sa.Column("resolved_by_id", sa.Uuid(), nullable=True),
        sa.Column("issue_type", sa.String(length=24), nullable=False),
        sa.Column("priority", sa.String(length=24), server_default="medium", nullable=False),
        sa.Column("status", sa.String(length=24), server_default="open", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["programme_enrollments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["reported_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    indexes(
        "operations_issues",
        "institution_id",
        "enrollment_id",
        "reported_by_id",
        "issue_type",
        "priority",
        "status",
    )


def downgrade() -> None:
    op.drop_table("operations_issues")
    op.drop_table("material_distributions")
    op.drop_table("training_materials")
    op.drop_table("participant_logistics")
    op.drop_table("bed_allocations")
    op.drop_table("hostel_beds")
    op.drop_table("hostel_rooms")
    op.drop_table("hostel_buildings")
    op.drop_table("timetable_sessions")
    op.drop_table("classrooms")
    op.drop_table("training_venues")
