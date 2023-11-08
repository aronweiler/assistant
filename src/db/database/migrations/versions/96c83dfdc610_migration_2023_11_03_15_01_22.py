"""migration 2023-11-03_15-01-22

Revision ID: 96c83dfdc610
Revises: 357436f888cc
Create Date: 2023-11-03 15:01:23.715100

"""
from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision = '96c83dfdc610'
down_revision = '357436f888cc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('documents', 'embedding', type_=pgvector.sqlalchemy.Vector())
    op.alter_column('documents', 'document_text_summary_embedding', type_=pgvector.sqlalchemy.Vector())
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###