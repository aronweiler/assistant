"""migration 2023-12-26_09-31-56

Revision ID: 9a7e026f2eb5
Revises: 94a7cdc82ec6
Create Date: 2023-12-26 09:31:57.277563

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a7e026f2eb5'
down_revision = '94a7cdc82ec6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('code_repositories_code_repository_address_key', 'code_repositories', type_='unique')
    op.create_unique_constraint(None, 'code_repositories', ['code_repository_address', 'branch_name'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'code_repositories', type_='unique')
    op.create_unique_constraint('code_repositories_code_repository_address_key', 'code_repositories', ['code_repository_address'])
    # ### end Alembic commands ###
