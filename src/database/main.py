import asyncio
import logging

from .database import create_tables

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


async def main():
    await create_tables()
    logger.info("Таблицы созданы")

if __name__ == "__main__":
    asyncio.run(main())
