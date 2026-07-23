import logging
import re
from datetime import date

from src.core.interfaces import Parser
from src.domain.protocols import UploadRepositoryProtocol

logger = logging.getLogger(__name__)


def extract_date_from_url(url: str) -> date | None:
    """
    Извлекает дату из URL вида:
      .../oil_20241217162000.pdf  или  .../oil_xls_20241217162000.xls
    Возвращает объект date (2024-12-17) или None, если дату не удалось распарсить.
    """
    match = re.search(r"(\d{4})(\d{2})(\d{2})\d{6}", url)
    if not match:
        logger.warning("Не удалось извлечь дату из URL: %s", url)
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    return date(year, month, day)


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
        saved_count = 0
        skipped_count = 0

        for url in reversed(urls):
            try:
                url_date = extract_date_from_url(url)

                if url_date is not None and await self._repository.url_exists_by_date(url_date):
                    skipped_count += 1
                    logger.warning("Пропущен дубликат по дате %s: %s", url_date, url)
                    continue

                await self._repository.add_url(url, date=url_date)
                saved_count += 1
                logger.info("[%d] Сохранено: %s (дата: %s)", saved_count, url, url_date)
            except Exception as e:
                logger.error("Ошибка при сохранении %s: %s", url, e)

        logger.info("Готово. Сохранено: %d, пропущено: %d", saved_count, skipped_count)
