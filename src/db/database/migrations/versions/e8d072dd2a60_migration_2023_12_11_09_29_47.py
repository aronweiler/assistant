"""migration 2023-12-11_09-29-47

Revision ID: e8d072dd2a60
Revises: 9449a9c475e5
Create Date: 2023-12-11 09:29:47.595956

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e8d072dd2a60'
down_revision = '9449a9c475e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_settings')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_settings',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('setting_name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('setting_value', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='user_settings_user_id_fkey'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='user_settings_user_id_fkey1'),
    sa.PrimaryKeyConstraint('id', name='user_settings_pkey')
    )
    # ### end Alembic commands ###
