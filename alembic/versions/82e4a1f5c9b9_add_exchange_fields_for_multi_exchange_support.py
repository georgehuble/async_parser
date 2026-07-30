"""add_exchange_fields_for_multi_exchange_support

Revision ID: 82e4a1f5c9b9
Revises: 1750d0754386
Create Date: 2026-07-30 22:35:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '82e4a1f5c9b9'
down_revision: str | Sequence[str] | None = '1750d0754386'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema — добавляем поля exchange для поддержки множественных бирж."""

    # --- oil_products ---
    # Добавляем поле exchange
    op.add_column('oil_products', sa.Column('exchange', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_oil_products_exchange'), 'oil_products', ['exchange'], unique=False)
    # Меняем unique constraint: убираем старый уникальный индекс на exchange_product_id,
    # создаём составной (exchange, exchange_product_id)
    op.drop_index('ix_oil_products_exchange_product_id', table_name='oil_products')
    op.create_index(op.f('ix_oil_products_exchange_product_id'), 'oil_products', ['exchange_product_id'], unique=False)
    op.create_unique_constraint('uix_oil_product_exchange', 'oil_products', ['exchange', 'exchange_product_id'])

    # --- trades ---
    # Добавляем поля exchange и exchange_trade_id
    op.add_column('trades', sa.Column('exchange', sa.String(length=50), nullable=False, server_default='UNKNOWN'))
    op.add_column('trades', sa.Column('exchange_trade_id', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_trades_exchange'), 'trades', ['exchange'], unique=False)

    # Меняем unique constraint: старый убираем, новый — (exchange, exchange_trade_id)
    op.drop_constraint('uix_trade_unique', 'trades', type_='unique')
    op.create_unique_constraint('uix_exchange_trade', 'trades', ['exchange', 'exchange_trade_id'])


def downgrade() -> None:
    """Downgrade schema — откатываем изменения."""

    # --- trades ---
    op.drop_constraint('uix_exchange_trade', 'trades', type_='unique')
    op.create_unique_constraint(
        'uix_trade_unique',
        'trades',
        ['product_id', 'delivery_basis_id', 'delivery_type_id', 'date'],
    )
    op.drop_index(op.f('ix_trades_exchange'), table_name='trades')
    op.drop_column('trades', 'exchange_trade_id')
    op.drop_column('trades', 'exchange')

    # --- oil_products ---
    op.drop_constraint('uix_oil_product_exchange', 'oil_products', type_='unique')
    op.drop_index(op.f('ix_oil_products_exchange_product_id'), table_name='oil_products')
    op.create_index(
        op.f('ix_oil_products_exchange_product_id'),
        'oil_products',
        ['exchange_product_id'],
        unique=True,
    )
    op.drop_index(op.f('ix_oil_products_exchange'), table_name='oil_products')
    op.drop_column('oil_products', 'exchange')
