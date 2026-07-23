import asyncio
import logging

from .database import create_tables

logger = logging.getLogger(__name__)


async def main():
    await create_tables()
    logger.info("Таблицы созданы")

if __name__ == "__main__":
    asyncio.run(main())
