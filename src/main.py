"""Точка входа приложения с ручным внедрением зависимостей (DI).

Здесь происходит сборка всех зависимостей вручную без использования DI-фреймворка.
Это единственное место, где высокоуровневый код импортирует конкретные реализации.
Также содержит оркестратор, координирующий парсинг и скачивание.
"""

import argparse
import asyncio
import logging

from src.application.downloaders.spimex_downloader import SpimexDownloader
from src.application.parsers.extract import ExtractService
from src.application.parsers.spimex_extractor import FILES_DIR, SpimexExtract
from src.application.parsers.spimex_fetch import SpimexFetch
from src.application.parsers.spimex_parser import SpimexParser
from src.application.parsers.upload import UploadService
from src.domain.interfaces.parsers import Downloader
from src.domain.interfaces.repositories import DownloadRepositoryAbstract
from src.infra.database import clear_all_tables, get_session
from src.infra.database.repositories import (
    DeliveryBasisRepository,
    DeliveryTypeRepository,
    ExchangeRepository,
    OilProductRepository,
    TradeRepository,
)

logger = logging.getLogger(__name__)

# Название биржи для источника SPIMEX (см. таблицу exchanges)
SPIMEX_NAME = "SPIMEX"


class Orchestrator:
    """Оркестратор, управляющий полным циклом: парсинг → сохранение → скачивание → извлечение."""

    def __init__(
        self,
        downloader: Downloader,
        upload_service: UploadService,
        download_repository: DownloadRepositoryAbstract,
        extract_service: ExtractService | None = None,
    ) -> None:
        """Инициализирует оркестратор.

        Args:
            downloader: Загрузчик файлов.
            upload_service: Сервис парсинга и сохранения ссылок в БД.
            download_repository: Репозиторий для получения ссылок на скачивание.
            extract_service: Сервис извлечения сделок из скачанных файлов.
        """
        self._downloader = downloader
        self._upload_service = upload_service
        self._download_repository = download_repository
        self._extract_service = extract_service

    async def run(self) -> None:
        """Выполняет полный цикл: парсинг → сохранение → скачивание → извлечение."""
        # Получаем максимальную дату из БД для ранней остановки парсинга
        max_date = await self._download_repository.get_max_date()

        # Шаг 1–2: Парсинг + сохранение ссылок в БД
        await self._upload_service.run(max_date=max_date)

        # Шаг 3: Получение ссылок для скачивания
        links = await self._download_repository.get_links()

        if links:
            logger.info("Запуск скачивания %d файлов...", len(links))
            await self._downloader.download(links)
        else:
            logger.info("Нет ссылок для скачивания.")

        # Шаг 4: Извлечение сделок из скачанных файлов и запись в БД
        if self._extract_service is not None:
            await self._extract_service.run()

        logger.info("Цикл завершён.")


async def main() -> None:
    """Собирает зависимости и запускает оркестратор."""
    arg_parser = argparse.ArgumentParser(description="Парсер с торгов СПб биржи")
    arg_parser.add_argument(
        "--clear",
        action="store_true",
        help="Очистить все таблицы БД перед запуском парсинга",
    )
    args = arg_parser.parse_args()

    logger.info("Сборка зависимостей...")

    # Создаём сессию БД и общий репозиторий сделок
    async with get_session() as session:
        if args.clear:
            logger.warning("Очистка всех таблиц БД перед запуском парсинга...")
            await clear_all_tables(session)

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
        fetch = SpimexFetch(parser=parser)
        downloader = SpimexDownloader(repository=trade_repository)

        # Создаём сервис загрузки ссылок (скачивание + сохранение в БД)
        upload_service = UploadService(
            fetcher=fetch,
            repository=trade_repository,
            exchange_id=exchange.exchange_id or 0,
            extract_date=parser.extract_date,
        )

        # Создаём сервис извлечения сделок из скачанных файлов
        extract = SpimexExtract(
            exchange_id=exchange.exchange_id or 0,
            trade_repository=trade_repository,
            oil_product_repository=OilProductRepository(session),
            delivery_basis_repository=DeliveryBasisRepository(session),
            delivery_type_repository=DeliveryTypeRepository(session),
        )
        extract_service = ExtractService(
            extractor=extract,
            files_dir=FILES_DIR,
        )

        # Собираем оркестратор
        orchestrator = Orchestrator(
            downloader=downloader,
            upload_service=upload_service,
            download_repository=trade_repository,
            extract_service=extract_service,
        )

        logger.info("Запуск оркестратора...")
        await orchestrator.run()
        logger.info("Оркестратор завершил работу.")


if __name__ == "__main__":
    asyncio.run(main())
