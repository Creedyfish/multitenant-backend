"""add full_name to users

Revision ID: 11f7e4799ed3
Revises: 6210dea27109
Create Date: 2026-02-25 00:54:37.709012

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "11f7e4799ed3"
down_revision: Union[str, Sequence[str], None] = "6210dea27109"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("full_name", sa.String(), nullable=False, server_default=""),
    )
    op.alter_column("users", "full_name", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "full_name")
