"""replace me

Revision ID: 66dad4e71257
Revises: 
Create Date: 2020-03-22 07:45:29.453905

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '66dad4e71257'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('tag',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default='now()', nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default='now()', nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('tag')
    # ### end Alembic commands ###
