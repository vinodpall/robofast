"""reset all tables

Revision ID: reset_all_tables
Revises: merge_robot_tables
Create Date: 2024-03-28

"""
from alembic import op
import sqlalchemy as sa
from app.models.models import RobotBodyType

# revision identifiers, used by Alembic.
revision = 'reset_all_tables'
down_revision = 'merge_robot_tables'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 删除所有现有表
    op.execute("DROP TABLE IF EXISTS robot")
    op.execute("DROP TABLE IF EXISTS robots")
    op.execute("DROP TABLE IF EXISTS task_records")
    op.execute("DROP TABLE IF EXISTS robot_types")
    op.execute("DROP TABLE IF EXISTS training_fields")
    op.execute("DROP TABLE IF EXISTS training_records")
    op.execute("DROP TABLE IF EXISTS entry_records")
    op.execute("DROP TABLE IF EXISTS award_records")
    op.execute("DROP TABLE IF EXISTS participation_records")
    op.execute("DROP TABLE IF EXISTS display_videos")
    
    # 创建新表
    op.create_table(
        'robots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('body_type', sa.Enum(RobotBodyType), nullable=False),
        sa.Column('brand', sa.String(50), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('serial_number', sa.String(50), nullable=False),
        sa.Column('create_date', sa.DateTime(), nullable=False),
        sa.Column('remarks', sa.String(255), nullable=True),
        sa.Column('image_url', sa.String(255), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('length', sa.Float(), nullable=True),
        sa.Column('width', sa.Float(), nullable=True),
        sa.Column('height', sa.Float(), nullable=True),
        sa.Column('skills', sa.JSON(), nullable=True),
        sa.Column('origin', sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('serial_number', name='uix_robot_serial_number'),
        sa.UniqueConstraint('name', 'brand', name='uix_robot_name_brand')
    )
    
    op.create_table(
        'robot_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uix_robot_type_name')
    )
    
    op.create_table(
        'training_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('scene_image_url', sa.String(255), nullable=True),
        sa.Column('monitor_image_url', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uix_training_field_name')
    )
    
    op.create_table(
        'training_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('robot_id', sa.Integer(), nullable=False),
        sa.Column('field_id', sa.Integer(), nullable=False),
        sa.Column('online', sa.Integer(), nullable=False, default=0),
        sa.Column('offline', sa.Integer(), nullable=False, default=0),
        sa.Column('fault', sa.Integer(), nullable=False, default=0),
        sa.Column('time', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['robot_id'], ['robots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['field_id'], ['training_fields.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'award_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('award_name', sa.String(100), nullable=False),
        sa.Column('award_level', sa.String(50), nullable=False),
        sa.Column('issuing_authority', sa.String(100), nullable=False),
        sa.Column('award_date', sa.DateTime(), nullable=False),
        sa.Column('certificate_image', sa.String(255), nullable=True),
        sa.Column('award_type', sa.String(20), nullable=False),
        sa.Column('robot_id', sa.Integer(), nullable=True),
        sa.Column('field_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['robot_id'], ['robots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['field_id'], ['training_fields.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('NOT(robot_id IS NULL AND field_id IS NULL) AND NOT(robot_id IS NOT NULL AND field_id IS NOT NULL)',
                          name='check_award_target')
    )
    
    op.create_table(
        'entry_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('robot_id', sa.Integer(), nullable=False),
        sa.Column('time', sa.DateTime(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, default=1),
        sa.ForeignKeyConstraint(['robot_id'], ['robots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'participation_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('visitor_count', sa.Integer(), nullable=False),
        sa.Column('time', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'display_videos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_url', sa.String(255), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    # 删除所有表
    op.drop_table('display_videos')
    op.drop_table('participation_records')
    op.drop_table('entry_records')
    op.drop_table('award_records')
    op.drop_table('training_records')
    op.drop_table('training_fields')
    op.drop_table('robot_types')
    op.drop_table('robots') 