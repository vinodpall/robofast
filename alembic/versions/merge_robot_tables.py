"""merge robot tables

Revision ID: merge_robot_tables
Revises: 
Create Date: 2024-03-28

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_robot_tables'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. 将robot表中的数据迁移到robots表
    op.execute("""
        INSERT IGNORE INTO robots (
            id, name, parameters, body_type, brand, price, 
            serial_number, create_date, remarks, image_url, 
            weight, length, width, height, skills, origin
        )
        SELECT 
            id, name, parameters, body_type, brand, price, 
            serial_number, create_date, remarks, image_url, 
            weight, length, width, height, skills, origin
        FROM robot
    """)

    # 2. 删除旧的robot表
    op.execute("DROP TABLE IF EXISTS robot")

def downgrade() -> None:
    # 由于是合并表操作，回滚操作将保持robots表不变
    pass 