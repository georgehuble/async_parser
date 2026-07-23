"""Оркестратор — высокоуровневый сервис, координирующий парсинг и скачивание.

Не зависит от конкретных реализаций — использует абстракции DataSource,
UploadRepositoryProtocol и DownloadRepositoryProtocol.
"""

import logging

from src.core.interfaces import DataSource
from src.domain.protocols import DownloadRepositoryProtocol, UploadRepositoryProtocol
from src.parser.upload import extract_date_from_url

logger = logging.getLogger(__name__)


class Orchestrator:
    """Оркестратор, управляющий полным циклом: парсинг → сохранение → скачивание."""

    def __init__(
        self,
        source: DataSource,
        upload_repository: UploadRepositoryProtocol,
        download_repository: DownloadRepositoryProtocol,
    ) -> None:
        """Инициализирует оркестратор.

        Args:
            source: Источник данных (объединяет парсер и загрузчик).
            upload_repository: Репозиторий для сохранения ссылок.
            download_repository: Репозиторий для получения ссылок на скачивание.
        """
        self._source = source
        self._upload_repository = upload_repository
        self._download_repository = download_repository

    async def run(self) -> None:
        """Выполняет полный цикл: парсинг → сохранение → скачивание."""
        # Шаг 1: Парсинг
        scraped_urls = await self._source.parse()

        if scraped_urls:
            logger.info("Парсер нашёл %d уникальных ссылок.", len(scraped_urls))
            # Шаг 2: Сохранение ссылок в БД
            await self._save_urls(scraped_urls)
        else:
            logger.info("Новых ссылок не найдено, переходим к скачиванию имеющихся.")

        # Шаг 3: Получение ссылок для скачивания
        links = await self._download_repository.get_links()

        if not links:
            logger.info("Нет ссылок для скачивания.")
            return

        # Шаг 4: Скачивание
        logger.info("Запуск скачивания %d файлов...", len(links))
        await self._source.download(links)
        logger.info("Цикл завершён.")

    async def _save_urls(self, urls: list[str]) -> None:
        """Сохраняет ссылки в БД через репозиторий."""
        saved_count = 0
        skipped_count = 0

        for url in reversed(urls):
            try:
                url_date = extract_date_from_url(url)

                if url_date is not None and await self._upload_repository.url_exists_by_date(url_date):
                    skipped_count += 1
                    logger.warning("Пропущен дубликат по дате %s: %s", url_date, url)
                    continue

                await self._upload_repository.add_url(url, date=url_date)
                saved_count += 1
                logger.info("[%d] Сохранено: %s (дата: %s)", saved_count, url, url_date)
            except Exception as e:
                logger.error("Ошибка при сохранении %s: %s", url, e)

        logger.info("Сохранение завершено: %d сохранено, %d пропущено.", saved_count, skipped_count)
