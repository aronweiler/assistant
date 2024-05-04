"""migration 2024-02-09_17-08-04

Revision ID: 242bd425a76c
Revises: 4aec00e27b34
Create Date: 2024-02-09 17:08:05.411354

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '242bd425a76c'
down_revision = '4aec00e27b34'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('code_file_dependencies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code_file_id', sa.Integer(), nullable=True),
    sa.Column('dependency_name', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['code_file_id'], ['code_files.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('code_file_dependencies')
    # ### end Alembic commands ###