import asyncio
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

sys.path.insert(0, str(ROOT_DIR))


from app.database import engine
from app.models import Base

async def main():
    print("🛠️  Создаем таблицы в базе данных...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Таблица 'spimex_trading_results' успешно создана!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
