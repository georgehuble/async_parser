import logging
from datetime import date

from src.domain.interfaces.parsers import Fetch
from src.domain.interfaces.repositories import UploadRepositoryAbstract
from src.domain.utils import save_urls

logger = logging.getLogger(__name__)


class UploadService:
    """Сервис для скачивания ссылок и сохранения их в БД.

    Принимает абстрактные Fetch и UploadRepositoryAbstract — не зависит
    от конкретных реализаций.
    """

    def __init__(self, parser: Fetch, repository: UploadRepositoryAbstract, exchange_id: int) -> None:
        """Инициализирует сервис.

        Args:
            parser: Абстрактный сканер страниц для получения ссылок.
            repository: Репозиторий для сохранения ссылок в БД.
            exchange_id: Идентификатор биржевого источника.
        """
        self._parser = parser
        self._repository = repository
        self._exchange_id = exchange_id

    async def run(self, max_date: date | None = None) -> list[str]:
        """Запускает парсинг и сохраняет ссылки в БД.

        Args:
            max_date: Максимальная дата для ранней остановки парсинга.
                     Если None — парсинг всех доступных страниц.

        Returns:
            Список сохранённых ссылок.
        """
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
            url_exists=self._repository.url_exists,
            add_url=self._repository.add_url,
            urls=urls,
            exchange_id=self._exchange_id,
            extract_date=self._parser.extract_date,
        )
