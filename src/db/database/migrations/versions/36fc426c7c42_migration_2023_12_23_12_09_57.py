"""migration 2023-12-23_12-09-57

Revision ID: 36fc426c7c42
Revises: ad8c266221c7
Create Date: 2023-12-23 12:09:57.441291

"""
from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision = '36fc426c7c42'
down_revision = 'ad8c266221c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('code_repositories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code_repository_address', sa.String(), nullable=False),
    sa.Column('branch_name', sa.String(), nullable=False),
    sa.Column('record_created', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code_repository_address')
    )
    op.create_table('code_files',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code_repository_id', sa.Integer(), nullable=False),
    sa.Column('code_file_name', sa.String(), nullable=False),
    sa.Column('code_file_commit', sa.String(), nullable=False),
    sa.Column('code_file_content', sa.String(), nullable=False),
    sa.Column('code_file_summary', sa.String(), nullable=False),
    sa.Column('code_file_summary_embedding', pgvector.sqlalchemy.Vector(), nullable=True),
    sa.Column('record_created', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['code_repository_id'], ['code_repositories.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code_repository_id', 'code_file_name')
    )
    op.add_column('conversations', sa.Column('last_selected_code_repo', sa.Integer(), nullable=False, server_default='-1'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('conversations', 'last_selected_code_repo')
    op.drop_table('code_files')
    op.drop_table('code_repositories')
    # ### end Alembic commands ###
