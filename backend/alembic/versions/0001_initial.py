"""Initial schema — all tables

Revision ID: 0001_initial
Revises: 
Create Date: 2026-03-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── devices ──────────────────────────────────────────────────────────────
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False, server_default="android"),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("fcm_token", sa.Text(), nullable=True),
        sa.Column("notification_listener_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_devices_id", "devices", ["id"])
    op.create_index("ix_devices_user_id", "devices", ["user_id"])

    # ── food_events ──────────────────────────────────────────────────────────
    op.create_table(
        "food_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_app", sa.String(100), nullable=True),
        sa.Column("raw_food_text", sa.Text(), nullable=True),
        sa.Column("normalized_food_text", sa.Text(), nullable=True),
        sa.Column("raw_notification_text", sa.Text(), nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("pincode", sa.String(20), nullable=True),
        sa.Column("meal_type", sa.String(50), nullable=True),
        sa.Column("is_processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_food_events_id", "food_events", ["id"])
    op.create_index("ix_food_events_user_id", "food_events", ["user_id"])
    op.create_index("ix_food_events_event_timestamp", "food_events", ["event_timestamp"])

    # ── food_classifications ──────────────────────────────────────────────────
    op.create_table(
        "food_classifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("food_category", sa.String(100), nullable=True),
        sa.Column("risk_tags", sa.Text(), nullable=True),
        sa.Column("matched_keywords", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("parse_quality", sa.String(20), nullable=False, server_default="complete"),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["event_id"], ["food_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_food_classifications_id", "food_classifications", ["id"])
    op.create_index("ix_food_classifications_event_id", "food_classifications", ["event_id"])

    # ── risk_scores ───────────────────────────────────────────────────────────
    op.create_table(
        "risk_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("base_food_risk", sa.Float(), nullable=False),
        sa.Column("time_multiplier", sa.Float(), nullable=False),
        sa.Column("behavior_multiplier", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("final_risk_score", sa.Float(), nullable=False),
        sa.Column("risk_band", sa.String(20), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["event_id"], ["food_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_risk_scores_id", "risk_scores", ["id"])
    op.create_index("ix_risk_scores_event_id", "risk_scores", ["event_id"])

    # ── nudges ────────────────────────────────────────────────────────────────
    op.create_table(
        "nudges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("nudge_text", sa.Text(), nullable=False),
        sa.Column("healthier_swap", sa.Text(), nullable=True),
        sa.Column("nudge_type", sa.String(50), nullable=False, server_default="risk_warning"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["event_id"], ["food_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_nudges_id", "nudges", ["id"])
    op.create_index("ix_nudges_event_id", "nudges", ["event_id"])
    op.create_index("ix_nudges_user_id", "nudges", ["user_id"])

    # ── user_aggregates ───────────────────────────────────────────────────────
    op.create_table(
        "user_aggregates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_label", sa.String(20), nullable=False, server_default="weekly"),
        sa.Column("avg_risk", sa.Float(), nullable=True),
        sa.Column("high_risk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("common_food_category", sa.String(100), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_aggregates_id", "user_aggregates", ["id"])
    op.create_index("ix_user_aggregates_user_id", "user_aggregates", ["user_id"])

    # ── heatmap_aggregates ────────────────────────────────────────────────────
    op.create_table(
        "heatmap_aggregates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("location_key", sa.String(100), nullable=False),
        sa.Column("pincode", sa.String(20), nullable=True),
        sa.Column("lat_bin", sa.Float(), nullable=True),
        sa.Column("lon_bin", sa.Float(), nullable=True),
        sa.Column("time_bucket", sa.String(50), nullable=False),
        sa.Column("hour_of_day", sa.Integer(), nullable=True),
        sa.Column("order_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_risk", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("high_risk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_risk_density", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("hotspot_intensity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_heatmap_aggregates_id", "heatmap_aggregates", ["id"])
    op.create_index("ix_heatmap_aggregates_location_key", "heatmap_aggregates", ["location_key"])
    op.create_index("ix_heatmap_aggregates_time_bucket", "heatmap_aggregates", ["time_bucket"])


def downgrade() -> None:
    op.drop_table("heatmap_aggregates")
    op.drop_table("user_aggregates")
    op.drop_table("nudges")
    op.drop_table("risk_scores")
    op.drop_table("food_classifications")
    op.drop_table("food_events")
    op.drop_table("devices")
    op.drop_table("users")
