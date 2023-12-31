"""migration 2023-12-25_11-04-05

Revision ID: 8ba5573d73d7
Revises: 2f060381eab6
Create Date: 2023-12-25 11:04:06.122553

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8ba5573d73d7'
down_revision = '2f060381eab6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('code_repository_files',
    sa.Column('code_repository_id', sa.Integer(), nullable=False),
    sa.Column('code_file_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['code_file_id'], ['code_files.id'], ),
    sa.ForeignKeyConstraint(['code_repository_id'], ['code_repositories.id'], ),
    sa.PrimaryKeyConstraint('code_repository_id', 'code_file_id')
    )
    op.add_column('code_files', sa.Column('code_file_valid', sa.Boolean(), nullable=False, default=True, server_default='True'))
    op.drop_constraint('code_files_code_repository_id_code_file_name_key', 'code_files', type_='unique')
    op.drop_constraint('code_files_code_repository_id_fkey', 'code_files', type_='foreignkey')
    op.drop_column('code_files', 'code_repository_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('code_files', sa.Column('code_repository_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key('code_files_code_repository_id_fkey', 'code_files', 'code_repositories', ['code_repository_id'], ['id'])
    op.create_unique_constraint('code_files_code_repository_id_code_file_name_key', 'code_files', ['code_repository_id', 'code_file_name'])
    op.drop_column('code_files', 'code_file_valid')
    op.drop_table('code_repository_files')
    # ### end Alembic commands ###
