"""add bio column

Revision ID: e1a2b3c4d5e6
Revises: d36ed3786a93
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa

revision = 'e1a2b3c4d5e6'
down_revision = '2c06a3338c82'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('bio', sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'bio')
