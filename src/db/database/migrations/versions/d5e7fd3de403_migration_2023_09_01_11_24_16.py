"""migration 2023-09-01_11-24-16

Revision ID: d5e7fd3de403
Revises: 4329e523e2cd
Create Date: 2023-09-01 11:24:17.144026

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5e7fd3de403'
down_revision = '4329e523e2cd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('files',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('collection_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('file_name', sa.String(), nullable=False),
    sa.Column('file_summary', sa.String(), nullable=True),
    sa.Column('file_contents', sa.String(), nullable=False),
    sa.Column('record_created', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['collection_id'], ['document_collections.id'], ),
    sa.ForeignKeyConstraint(['collection_id'], ['document_collections.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('documents', sa.Column('file_id', sa.Integer(), nullable=False))
    op.create_foreign_key(None, 'documents', 'files', ['file_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'documents', type_='foreignkey')
    op.drop_column('documents', 'file_id')
    op.drop_table('files')
    # ### end Alembic commands ###