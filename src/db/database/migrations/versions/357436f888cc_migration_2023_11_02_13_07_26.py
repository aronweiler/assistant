"""migration 2023-11-02_13-07-26

Revision ID: 357436f888cc
Revises: 465bf24a43ce
Create Date: 2023-11-02 13:07:26.669062

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '357436f888cc'
down_revision = '465bf24a43ce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('document_collections', sa.Column('collection_type', sa.String(), nullable=False, server_default="Remote (OpenAI)"))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('document_collections', 'collection_type')
    # ### end Alembic commands ###