"""Заглушка загрузчика для MOEX."""

import logging
from datetime import date

from src.domain.interfaces import Downloader

logger = logging.getLogger(__name__)


class MoexDownloader(Downloader):
    """Загрузчик файлов с сайта MOEX (заглушка)."""

    async def download(self, links: list[tuple[date, str]]) -> None:
        """Заглушка: просто логирует."""
        logger.info("MoexDownloader.download() — заглушка, получено %d ссылок", len(links))
