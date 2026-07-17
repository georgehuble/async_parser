import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.models import Parsered


async def save_to_database(df: pd.DataFrame, session: AsyncSession, batch_size: int = 500) -> int:
    if df.empty:
        print("DataFrame пуст, нечего сохранять")
        return 0

    records = df.to_dict('records')
    total_saved = 0

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(records) + batch_size - 1) // batch_size

        print(f"Сохраняем батч {batch_num} из {total_batches} ({len(batch)} строк)...")

        stmt = insert(Parsered).values(batch)

        stmt = stmt.on_conflict_do_update(
            index_elements=['exchange_product_id', 'delivery_basis_name', 'date'],
            set_={
                'exchange_product_name': stmt.excluded.exchange_product_name,
                'oil_id': stmt.excluded.oil_id,
                'delivery_basis_id': stmt.excluded.delivery_basis_id,
                'delivery_type_id': stmt.excluded.delivery_type_id,
                'volume': stmt.excluded.volume,
                'total': stmt.excluded.total,
                'count': stmt.excluded.count,
                'updated_on': func.now(),
            }
        )

        await session.execute(stmt)
        await session.commit()
        total_saved += len(batch)

    print(f"Успешно сохранено/обновлено {total_saved} строк")
    return total_saved


async def check_database_stats(session: AsyncSession) -> dict:

    result = await session.execute(select(Parsered))
    records = result.scalars().all()

    stats = {
        'total_records': len(records),
        'date_range': {
            'min': min(r.date for r in records) if records else None,
            'max': max(r.date for r in records) if records else None,
        }
    }

    return stats
