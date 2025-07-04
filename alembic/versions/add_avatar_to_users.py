"""Add avatar_url to users table

Revision ID: add_avatar_to_users
Revises: 
Create Date: 2025-01-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_avatar_to_users'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add avatar_url column to users table
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))


def downgrade():
    # Remove avatar_url column from users table
    op.drop_column('users', 'avatar_url')
