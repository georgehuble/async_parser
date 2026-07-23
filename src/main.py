"""Точка входа приложения с ручным внедрением зависимостей (DI).

Здесь происходит сборка всех зависимостей вручную без использования DI-фреймворка.
Это единственное место, где высокоуровневый код импортирует конкретные реализации.
"""

import asyncio
import logging

from src.database import get_session
from src.database.repository import SpimexDownloadRepository, SpimexUploadRepository
from src.datasource.spimex_datasource import SpimexDataSource
from src.downloader.spimex_downloader import SpimexDownloader
from src.orchestrator import Orchestrator
from src.parser.spimex_parser import SpimexParser
from src.parser.upload import UploadService

logger = logging.getLogger(__name__)


async def main() -> None:
    """Собирает зависимости и запускает оркестратор."""
    logger.info("Сборка зависимостей...")

    # Создаём сессию БД и репозитории
    async with get_session() as session:
        upload_repository = SpimexUploadRepository(session)
        download_repository = SpimexDownloadRepository(session)

        # Получаем максимальную дату из БД для ранней остановки парсинга
        max_date = await download_repository.get_max_date()
        logger.info("Максимальная дата в БД: %s", max_date)

        # Создаём конкретные реализации
        parser = SpimexParser(max_date=max_date)
        downloader = SpimexDownloader(repository=download_repository)
        source = SpimexDataSource(parser=parser, downloader=downloader)

        # Создаём сервис загрузки ссылок (парсинг + сохранение в БД)
        upload_service = UploadService(parser=parser, repository=upload_repository)

        # Собираем оркестратор
        orchestrator = Orchestrator(
            source=source,
            upload_service=upload_service,
            download_repository=download_repository,
        )

        logger.info("Запуск оркестратора...")
        await orchestrator.run()
        logger.info("Оркестратор завершил работу.")


if __name__ == "__main__":
    asyncio.run(main())
