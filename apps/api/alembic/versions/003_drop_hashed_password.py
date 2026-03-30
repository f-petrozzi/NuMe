"""Drop legacy password column from users

Revision ID: 003
Revises: 002
Create Date: 2026-03-28
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "hashed_password")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.String(length=255), nullable=False, server_default=""),
    )
    op.alter_column("users", "hashed_password", server_default=None)
