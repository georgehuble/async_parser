"""Скачивание страниц сайта Spimex (HTTP-запросы и пагинация).

Класс отвечает только за скачивание (fetch) HTML-страниц и перебор
пагинации. Разбор HTML делегируется абстракции ``Parser`` для
определения момента остановки перебора страниц (SRP, DIP).
"""

import asyncio
import logging
from datetime import date

import aiohttp

from src.application.parsers.spimex_config import BASE_URL
from src.domain.interfaces.parsers.fetch import Fetch
from src.domain.interfaces.parsers.parser import Parser, StopReason

logger = logging.getLogger(__name__)


class SpimexFetch(Fetch):
    """Сканер страниц сайта Spimex.

    Скачивает HTML-страницы пагинации и собирает ссылки на бюллетени.
    Сам HTML не разбирает — эту обязанность выполняет ``Parser`` (DIP).
    """

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; Spimex/1.0)",
        "Accept-Encoding": "gzip, deflate",
    }
    BATCH_SIZE = 10

    def __init__(self, parser: Parser) -> None:
        """Инициализирует сканер страниц.

        Args:
            parser: Разбор HTML-страницы (SRP).
        """
        self._parser = parser

    async def fetch_html(self, url: str) -> str:
        """Отправляет HTTP-запрос по URL и возвращает HTML-страницу.

        Args:
            url: URL страницы для скачивания.

        Returns:
            HTML-содержимое страницы.
        """
        async with aiohttp.ClientSession(headers=self.HEADERS) as session:
            async with session.get(url) as response:
                return await response.text()

    def _build_batch_urls(self, page: int) -> list[str]:
        """Строит URL пакета страниц пагинации."""
        return [
            f"{BASE_URL}/markets/oil_products/trades/results/?page=page-{p}"
            for p in range(page, page + self.BATCH_SIZE)
        ]

    async def _fetch_and_parse(
        self,
        session: aiohttp.ClientSession,
        url: str,
        max_date: date | None,
    ) -> tuple[list[str], StopReason]:
        """Скачивает HTML и делегирует разбор страницы в отдельный поток."""
        try:
            async with session.get(url) as response:
                html = await response.text()
            return await asyncio.to_thread(self._parser.parse_links, html, max_date)
        except Exception as e:
            logger.error(f"Ошибка при обработке {url}: {e}")
            return [], StopReason.CONTINUE

    async def collect_links(self, max_date: date | None = None) -> list[str]:
        """Обходит страницы сайта и возвращает список ссылок.

        Args:
            max_date: Максимальная дата для ранней остановки обхода.
        """
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit_per_host=30)
        result: list[str] = []
        seen_links: set[str] = set()
        page = 1

        async with aiohttp.ClientSession(headers=self.HEADERS, timeout=timeout, connector=connector) as session:
            while True:
                urls = self._build_batch_urls(page)
                logger.info(f"Загрузка пакета страниц: {page} - {page + self.BATCH_SIZE - 1}")

                stop_reason = StopReason.CONTINUE
                has_new_links = False

                for url in urls:
                    links, reason = await self._fetch_and_parse(session, url, max_date)

                    if reason is StopReason.CUTOFF:
                        stop_reason = StopReason.CUTOFF
                        break
                    elif reason is StopReason.MAX_DATE:
                        stop_reason = StopReason.MAX_DATE
                        # Не прерываем — на следующих страницах могут быть новые даты

                    new_links = [link for link in links if link not in seen_links]
                    if new_links:
                        has_new_links = True
                        seen_links.update(new_links)
                        result.extend(new_links)

                if stop_reason is StopReason.CUTOFF:
                    logger.info("Достигнут предельный год. Завершение.")
                    break

                # Завершаемся, если на всех страницах пачки не было новых ссылок,
                # и при этом есть причина остановки (значит, зацепились за дату из БД)
                if not has_new_links and stop_reason is StopReason.MAX_DATE:
                    logger.info("Новые ссылки не найдены, все даты уже есть в БД. Завершение.")
                    break

                if not has_new_links:
                    logger.info("Новые ссылки не найдены.")
                    break

                page += self.BATCH_SIZE

        return result
