"""Оркестратор — высокоуровневый сервис, координирующий парсинг и скачивание.

Не зависит от конкретных реализаций — использует абстракции DataSource,
UploadService и DownloadRepositoryProtocol.
"""

import logging

from src.core.interfaces import DataSource
from src.domain.protocols import DownloadRepositoryProtocol
from src.parser.upload import UploadService

logger = logging.getLogger(__name__)


class Orchestrator:
    """Оркестратор, управляющий полным циклом: парсинг → сохранение → скачивание."""

    def __init__(
        self,
        source: DataSource,
        upload_service: UploadService,
        download_repository: DownloadRepositoryProtocol,
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
