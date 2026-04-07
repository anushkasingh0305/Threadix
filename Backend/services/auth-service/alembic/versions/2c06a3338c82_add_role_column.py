"""add role column

Revision ID: 2c06a3338c82
Revises: d36ed3786a93
Create Date: 2026-04-03 13:17:13.469341

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c06a3338c82'
down_revision: Union[str, Sequence[str], None] = 'd36ed3786a93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'moderator', 'member')")
    op.add_column('users', sa.Column('role', sa.Enum('admin', 'moderator', 'member', name='userrole', create_type=False), nullable=True, server_default='member'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'role')
    op.execute("DROP TYPE userrole")
