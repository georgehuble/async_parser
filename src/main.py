"""Точка входа приложения с ручным внедрением зависимостей (DI).

Здесь происходит сборка всех зависимостей вручную без использования DI-фреймворка.
Это единственное место, где высокоуровневый код импортирует конкретные реализации.
"""

import asyncio
import logging

from src.database import get_session
from src.database.repository import SpimexRepository
from src.datasource.spimex_datasource import SpimexDataSource
from src.downloader.spimex_downloader import SpimexDownloader
from src.orchestrator import Orchestrator
from src.parser.spimex_parser import SpimexParser

logger = logging.getLogger(__name__)


async def main() -> None:
    """Собирает зависимости и запускает оркестратор."""
    logger.info("Сборка зависимостей...")

    # Создаём сессию БД и репозиторий
    async with get_session() as session:
        repository = SpimexRepository(session)

        # Получаем максимальную дату из БД для ранней остановки парсинга
        max_date = await repository.get_max_date()
        logger.info("Максимальная дата в БД: %s", max_date)

        # Создаём конкретные реализации
        parser = SpimexParser(max_date=max_date)
        downloader = SpimexDownloader(repository=repository)
        source = SpimexDataSource(parser=parser, downloader=downloader)

        # Собираем оркестратор
        orchestrator = Orchestrator(
            source=source,
            upload_repository=repository,
            download_repository=repository,
        )

        logger.info("Запуск оркестратора...")
        await orchestrator.run()
        logger.info("Оркестратор завершил работу.")


if __name__ == "__main__":
    asyncio.run(main())
