"""migration 2024-03-17_21-51-23

Revision ID: 77a7bf48aaa7
Revises: e5d3eb330b02
Create Date: 2024-03-17 21:51:24.544340

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '77a7bf48aaa7'
down_revision = 'e5d3eb330b02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('document_collections_collection_name_key', 'document_collections', type_='unique')
    op.create_unique_constraint(None, 'document_collections', ['user_id', 'collection_name'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'document_collections', type_='unique')
    op.create_unique_constraint('document_collections_collection_name_key', 'document_collections', ['collection_name'])
    # ### end Alembic commands ###