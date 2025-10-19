"""add titulo_adaptado field

Revision ID: add_titulo_adaptado
Revises: 
Create Date: 2025-10-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_titulo_adaptado'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Añadir campo titulo_adaptado a la tabla licitaciones
    op.add_column('licitaciones', sa.Column('titulo_adaptado', sa.Text(), nullable=True))

def downgrade():
    # Eliminar campo titulo_adaptado
    op.drop_column('licitaciones', 'titulo_adaptado')
