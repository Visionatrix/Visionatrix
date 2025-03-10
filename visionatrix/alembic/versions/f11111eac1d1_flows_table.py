"""Flows tables

Revision ID: f01666eac6d5
Revises: 87e327306368
Create Date: 2025-03-10 11:54:39.522692

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f11111eac1d1"
down_revision: str | None = "90b4e0fa8d34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "flows_install_status", sa.Column("installed", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.execute("UPDATE flows_install_status SET installed = true WHERE progress = 100")
    op.drop_column("flows_install_status", "progress")
    op.create_index(op.f("ix_flows_install_status_installed"), "flows_install_status", ["installed"], unique=False)
    op.add_column("flows_install_status", sa.Column("models", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.add_column(
        "flows_install_status", sa.Column("progress", sa.Float(), nullable=False, server_default=sa.text("0.0"))
    )
    op.execute("UPDATE flows_install_status SET progress = 100 WHERE installed = true")
    op.execute("UPDATE flows_install_status SET progress = 0 WHERE installed = false")
    op.drop_index(op.f("ix_flows_install_status_installed"), table_name="flows_install_status")
    op.drop_column("flows_install_status", "installed")
    op.drop_column("flows_install_status", "models")
