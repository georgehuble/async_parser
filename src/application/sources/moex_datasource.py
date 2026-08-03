"""Источник данных MOEX (заглушка для проверки OCP)."""

import logging
from datetime import date

from src.domain.interfaces.parsers import DataSource, Downloader, Fetch

logger = logging.getLogger(__name__)


class MoexDataSource(DataSource):
    """Источник данных для сайта MOEX (заглушка).

    Создан для проверки OCP — ни один существующий файл не изменён.
    """

    def __init__(self, parser: Fetch, downloader: Downloader) -> None:
        self._parser = parser
        self._downloader = downloader

    async def parse(self) -> list[str]:
        return await self._parser.parse()

    async def download(self, links: list[tuple[date, str]]) -> None:
        await self._downloader.download(links)
