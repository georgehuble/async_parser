import logging
from datetime import date

from src.domain.interfaces import Parser
from src.domain.protocols import UploadRepositoryProtocol
from src.domain.utils import save_urls

logger = logging.getLogger(__name__)


class UploadService:
    """Сервис для парсинга ссылок и сохранения их в БД.

    Принимает абстрактные Parser и UploadRepositoryProtocol — не зависит
    от конкретных реализаций.
    """

    def __init__(self, parser: Parser, repository: UploadRepositoryProtocol) -> None:
        """Инициализирует сервис.

        Args:
            parser: Абстрактный парсер для получения ссылок.
            repository: Репозиторий для сохранения ссылок в БД.
        """
        self._parser = parser
        self._repository = repository

    async def run(self, max_date: date | None = None) -> list[str]:
        """Запускает парсинг и сохраняет ссылки в БД.

        Args:
            max_date: Максимальная дата для парсинга.
                     Если None — парсинг всех доступных страниц.

        Returns:
            Список сохранённых ссылок.
        """
        # Если в БД уже есть запись с max_date — данные актуальны, парсинг не нужен
        if max_date is not None and await self._repository.url_exists_by_date(max_date):
            logger.info(
                "В БД уже есть данные за %s. Парсинг не требуется.",
                max_date,
            )
            return []

        logger.info("Запуск парсера...")
        if max_date:
            logger.info("Парсер остановится <= %s", max_date)
        else:
            logger.info("Парсинг всех доступных страниц")

        # Устанавливаем max_date в парсер, если поддерживается
        if hasattr(self._parser, "max_date"):
            self._parser.max_date = max_date  # type: ignore[union-attr]

        scraped_urls = await self._parser.parse()

        if not scraped_urls:
            logger.info("Ссылки не найдены.")
            return []

        logger.info("Парсер нашёл %d уникальных ссылок.", len(scraped_urls))
        await self._save_urls(scraped_urls)
        return scraped_urls

    async def _save_urls(self, urls: list[str]) -> None:
        """Сохраняет ссылки в БД через репозиторий."""
        await save_urls(
            url_exists_by_date=self._repository.url_exists_by_date,
            add_url=self._repository.add_url,
            urls=urls,
            extract_date=self._parser.extract_date,
        )
