"""Add civil defense fields to requests table

Revision ID: add_civil_defense_fields
Revises: add_avatar_to_users
Create Date: 2024-12-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_civil_defense_fields'
down_revision = 'add_avatar_to_users'
branch_labels = None
depends_on = None


def upgrade():
    """Add new civil defense fields to requests table"""
    # Add personal information fields
    op.add_column('requests', sa.Column('full_name', sa.String(200), nullable=True))
    op.add_column('requests', sa.Column('personal_number', sa.String(9), nullable=True))
    
    # Add building information fields
    op.add_column('requests', sa.Column('building_name', sa.String(200), nullable=True))
    op.add_column('requests', sa.Column('road_name', sa.String(200), nullable=True))
    op.add_column('requests', sa.Column('building_number', sa.String(100), nullable=True))
    op.add_column('requests', sa.Column('civil_defense_file_number', sa.String(100), nullable=True))
    op.add_column('requests', sa.Column('building_permit_number', sa.String(100), nullable=True))
    
    # Add license section checkboxes
    op.add_column('requests', sa.Column('licenses_section', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('requests', sa.Column('fire_equipment_section', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('requests', sa.Column('commercial_records_section', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('requests', sa.Column('engineering_offices_section', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('requests', sa.Column('hazardous_materials_section', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add file category field to files table
    op.add_column('files', sa.Column('file_category', sa.String(100), nullable=True))
    
    # Update existing records with default values
    op.execute("UPDATE requests SET full_name = request_name WHERE full_name IS NULL")
    op.execute("UPDATE requests SET personal_number = '000000000' WHERE personal_number IS NULL")
    op.execute("UPDATE files SET file_category = 'general' WHERE file_category IS NULL")
    
    # Make required fields non-nullable after setting defaults
    op.alter_column('requests', 'full_name', nullable=False)
    op.alter_column('requests', 'personal_number', nullable=False)
    op.alter_column('files', 'file_category', nullable=False)


def downgrade():
    """Remove civil defense fields from requests table"""
    # Remove personal information fields
    op.drop_column('requests', 'full_name')
    op.drop_column('requests', 'personal_number')
    
    # Remove building information fields
    op.drop_column('requests', 'building_name')
    op.drop_column('requests', 'road_name')
    op.drop_column('requests', 'building_number')
    op.drop_column('requests', 'civil_defense_file_number')
    op.drop_column('requests', 'building_permit_number')
    
    # Remove license section checkboxes
    op.drop_column('requests', 'licenses_section')
    op.drop_column('requests', 'fire_equipment_section')
    op.drop_column('requests', 'commercial_records_section')
    op.drop_column('requests', 'engineering_offices_section')
    op.drop_column('requests', 'hazardous_materials_section')
    
    # Remove file category field
    op.drop_column('files', 'file_category')
