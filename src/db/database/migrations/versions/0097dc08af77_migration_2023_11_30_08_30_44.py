"""migration 2023-11-30_08-30-44

Revision ID: 0097dc08af77
Revises: 96c83dfdc610
Create Date: 2023-11-30 08:30:45.455047

"""
from alembic import op
import sqlalchemy as sa
import pgvector


# revision identifiers, used by Alembic.
revision = '0097dc08af77'
down_revision = '96c83dfdc610'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('documents', sa.Column('embedding_question_1', pgvector.sqlalchemy.Vector(), nullable=True))
    op.add_column('documents', sa.Column('embedding_question_2', pgvector.sqlalchemy.Vector(), nullable=True))
    op.add_column('documents', sa.Column('embedding_question_3', pgvector.sqlalchemy.Vector(), nullable=True))
    op.add_column('documents', sa.Column('embedding_question_4', pgvector.sqlalchemy.Vector(), nullable=True))
    op.add_column('documents', sa.Column('embedding_question_5', pgvector.sqlalchemy.Vector(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('documents', 'embedding_question_5')
    op.drop_column('documents', 'embedding_question_4')
    op.drop_column('documents', 'embedding_question_3')
    op.drop_column('documents', 'embedding_question_2')
    op.drop_column('documents', 'embedding_question_1')
    # ### end Alembic commands ###