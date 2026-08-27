import logging
from datetime import date

from src.domain.interfaces.parsers import Fetch
from src.domain.interfaces.repositories import UploadRepositoryAbstract
from src.domain.utils import ExtractDateFn, save_urls

logger = logging.getLogger(__name__)


class UploadService:
    """Сервис для сбора ссылок и сохранения их в БД.

    Принимает абстрактный Fetch, функцию извлечения даты из URL и
    UploadRepositoryAbstract — не зависит от конкретных реализаций.
    """

    def __init__(
        self,
        fetcher: Fetch,
        repository: UploadRepositoryAbstract,
        exchange_id: int,
        extract_date: ExtractDateFn | None = None,
    ) -> None:
        """Инициализирует сервис.

        Args:
            fetcher: Абстрактный сканер страниц для получения ссылок.
            repository: Репозиторий для сохранения ссылок в БД.
            exchange_id: Идентификатор биржевого источника.
            extract_date: Функция извлечения даты из URL.
        """
        self._fetcher = fetcher
        self._repository = repository
        self._exchange_id = exchange_id
        self._extract_date = extract_date

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

        scraped_urls = await self._fetcher.collect_links(max_date=max_date)

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
            extract_date=self._extract_date,
        )
