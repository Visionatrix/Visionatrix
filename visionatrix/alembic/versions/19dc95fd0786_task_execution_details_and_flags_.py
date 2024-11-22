"""Added execution_details column to task_details table

Revision ID: 19dc95fd0786
Revises: 4ec7ae538cfb
Create Date: 2024-11-10 09:03:31.044376

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "19dc95fd0786"
down_revision: str | None = "4ec7ae538cfb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("tasks_details", sa.Column("execution_details", sa.JSON(), nullable=True))
    op.add_column("tasks_details", sa.Column("extra_flags", sa.JSON(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("tasks_details", "execution_details")
    op.drop_column("tasks_details", "extra_flags")
    # ### end Alembic commands ###