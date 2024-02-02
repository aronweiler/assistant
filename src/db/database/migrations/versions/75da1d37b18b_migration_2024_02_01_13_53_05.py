"""migration 2024-02-01_13-53-05

Revision ID: 75da1d37b18b
Revises: 4a6da61416a8
Create Date: 2024-02-01 13:53:06.335353

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '75da1d37b18b'
down_revision = '4a6da61416a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('setting_name', sa.String(), nullable=False),
    sa.Column('setting_value', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_settings')
    # ### end Alembic commands ###