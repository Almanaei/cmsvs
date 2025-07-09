"""Add user approval status field

Revision ID: add_user_approval_status
Revises: add_civil_defense_fields
Create Date: 2025-01-28 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_user_approval_status'
down_revision = 'add_details_to_activities'
branch_labels = None
depends_on = None


def upgrade():
    # Create the enum type for user status
    user_status_enum = sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='userstatus')
    user_status_enum.create(op.get_bind())
    
    # Add approval_status column to users table
    op.add_column('users', sa.Column('approval_status', user_status_enum, nullable=False, server_default='PENDING'))


def downgrade():
    # Remove approval_status column from users table
    op.drop_column('users', 'approval_status')
    
    # Drop the enum type
    user_status_enum = sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='userstatus')
    user_status_enum.drop(op.get_bind())
