import logging
from datetime import date

from src.core.interfaces import DataSource, Downloader, Parser

logger = logging.getLogger(__name__)


class SpimexDataSource(DataSource):
    """Источник данных для сайта Spimex.

    Композиция парсера и загрузчика Spimex.
    Не содержит логики, специфичной для Spimex — только делегирование.
    """

    def __init__(self, parser: Parser, downloader: Downloader) -> None:
        """Инициализирует источник данных.

        Args:
            parser: Парсер для получения ссылок.
            downloader: Загрузчик для скачивания файлов.
        """
        self._parser = parser
        self._downloader = downloader

    async def parse(self) -> list[str]:
        """Делегирует парсинг внутреннему парсеру."""
        return await self._parser.parse()

    async def download(self, links: list[tuple[date, str]]) -> None:
        """Делегирует загрузку внутреннему загрузчику."""
        await self._downloader.download(links)
