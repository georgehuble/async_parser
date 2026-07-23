"""add unique constraint on url

Revision ID: 429b9702bfa4
Revises: 6246f2c10e17
Create Date: 2026-07-23 13:51:05.910023

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '429b9702bfa4'
down_revision: str | Sequence[str] | None = '6246f2c10e17'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint('uq_results_url', 'results', ['url'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_results_url', 'results', type_='unique')
