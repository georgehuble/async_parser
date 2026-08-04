"""Точка входа приложения с ручным внедрением зависимостей (DI).

Здесь происходит сборка всех зависимостей вручную без использования DI-фреймворка.
Это единственное место, где высокоуровневый код импортирует конкретные реализации.
Также содержит оркестратор, координирующий парсинг и скачивание.
"""

import asyncio
import logging

from src.application.downloaders.spimex_downloader import SpimexDownloader
from src.application.parsers.spimex_fetch import SpimexFetch
from src.application.parsers.spimex_parser import SpimexParser
from src.application.parsers.upload import UploadService
from src.application.sources.spimex_datasource import SpimexDataSource
from src.domain.interfaces.parsers import DataSource
from src.domain.interfaces.repositories import DownloadRepositoryAbstract
from src.infra.database import get_session
from src.infra.database.repositories import ExchangeRepository, TradeRepository

logger = logging.getLogger(__name__)

# Название биржи для источника SPIMEX (см. таблицу exchanges)
SPIMEX_NAME = "SPIMEX"


class Orchestrator:
    """Оркестратор, управляющий полным циклом: парсинг → сохранение → скачивание."""

    def __init__(
        self,
        source: DataSource,
        upload_service: UploadService,
        download_repository: DownloadRepositoryAbstract,
    ) -> None:
        """Инициализирует оркестратор.

        Args:
            source: Источник данных (для скачивания файлов).
            upload_service: Сервис парсинга и сохранения ссылок в БД.
            download_repository: Репозиторий для получения ссылок на скачивание.
        """
        self._source = source
        self._upload_service = upload_service
        self._download_repository = download_repository

    async def run(self) -> None:
        """Выполняет полный цикл: парсинг → сохранение → скачивание."""
        # Получаем максимальную дату из БД для ранней остановки парсинга
        max_date = await self._download_repository.get_max_date()

        # Шаг 1–2: Парсинг + сохранение ссылок в БД
        await self._upload_service.run(max_date=max_date)

        # Шаг 3: Получение ссылок для скачивания
        links = await self._download_repository.get_links()

        if not links:
            logger.info("Нет ссылок для скачивания.")
            return

        # Шаг 4: Скачивание
        logger.info("Запуск скачивания %d файлов...", len(links))
        await self._source.download(links)
        logger.info("Цикл завершён.")


async def main() -> None:
    """Собирает зависимости и запускает оркестратор."""
    logger.info("Сборка зависимостей...")

    # Создаём сессию БД и общий репозиторий сделок
    async with get_session() as session:
        trade_repository = TradeRepository(session)
        exchange_repository = ExchangeRepository(session)

        # Получаем (или создаём) биржевой источник SPIMEX
        exchange = await exchange_repository.get_or_create_by_name(SPIMEX_NAME)
        logger.info("Биржевой источник: %s (id=%s)", exchange.name, exchange.exchange_id)

        # Получаем максимальную дату из БД для ранней остановки парсинга
        max_date = await trade_repository.get_max_date()
        logger.info("Максимальная дата в БД: %s", max_date)

        # Создаём конкретные реализации
        parser = SpimexParser()
        fetch = SpimexFetch(parser=parser, max_date=max_date)
        downloader = SpimexDownloader(repository=trade_repository)
        source = SpimexDataSource(parser=fetch, downloader=downloader)

        # Создаём сервис загрузки ссылок (скачивание + сохранение в БД)
        upload_service = UploadService(
            parser=fetch,
            repository=trade_repository,
            exchange_id=exchange.exchange_id or 0,
        )

        # Собираем оркестратор
        orchestrator = Orchestrator(
            source=source,
            upload_service=upload_service,
            download_repository=trade_repository,
        )

        logger.info("Запуск оркестратора...")
        await orchestrator.run()
        logger.info("Оркестратор завершил работу.")


if __name__ == "__main__":
    asyncio.run(main())
