"""Add details column to activities table

Revision ID: add_details_to_activities
Revises: add_civil_defense_fields
Create Date: 2025-01-28 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'add_details_to_activities'
down_revision = 'add_civil_defense_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Add details column to activities table"""
    # Add details column as JSON type
    op.add_column('activities', sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade():
    """Remove details column from activities table"""
    op.drop_column('activities', 'details')
