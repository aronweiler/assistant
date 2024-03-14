"""migration 2024-03-12_17-00-50

Revision ID: ec8f10d5a2f7
Revises: d8992a7d7e6a
Create Date: 2024-03-12 17:00:51.736664

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ec8f10d5a2f7'
down_revision = 'd8992a7d7e6a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('password_hash', sa.String(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'password_hash')
    # ### end Alembic commands ###