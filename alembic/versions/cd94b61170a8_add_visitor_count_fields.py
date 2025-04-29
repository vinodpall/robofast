"""add visitor count fields

Revision ID: cd94b61170a8
Revises: remove_video_url
Create Date: 2024-03-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd94b61170a8'
down_revision: Union[str, None] = 'remove_video_url'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加新字段
    op.add_column('web_configs', sa.Column('weekly_visitor_count', sa.Integer(), nullable=True))
    op.add_column('web_configs', sa.Column('monthly_visitor_count', sa.Integer(), nullable=True))
    op.add_column('web_configs', sa.Column('video_carousel_duration', sa.Integer(), nullable=True))


def downgrade() -> None:
    # 删除新字段
    op.drop_column('web_configs', 'weekly_visitor_count')
    op.drop_column('web_configs', 'monthly_visitor_count')
    op.drop_column('web_configs', 'video_carousel_duration') 