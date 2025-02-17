"""Recreate migration

Revision ID: fb1884e487a4
Revises: 96e2e30f3123
Create Date: 2025-02-07 18:39:34.013022

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fb1884e487a4'
down_revision = '96e2e30f3123'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.alter_column('body',
               existing_type=sa.VARCHAR(length=140),
               type_=sa.String(length=10000),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.alter_column('body',
               existing_type=sa.String(length=10000),
               type_=sa.VARCHAR(length=140),
               existing_nullable=False)

    # ### end Alembic commands ###
