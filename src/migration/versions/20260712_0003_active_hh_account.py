"""Add active HH account id."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260712_0003"
down_revision = "20260711_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("active_hh_account_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_table(
        "oauth_state_nonces",
        sa.Column("nonce", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("nonce"),
    )
    op.create_index("ix_oauth_state_nonces_expires_at", "oauth_state_nonces", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_oauth_state_nonces_expires_at", table_name="oauth_state_nonces")
    op.drop_table("oauth_state_nonces")
    op.drop_column("users", "active_hh_account_id")
