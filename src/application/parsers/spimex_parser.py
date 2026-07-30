import asyncio
import logging
import re
from datetime import date, datetime
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from src.domain.interfaces.parsers import Parser

logger = logging.getLogger(__name__)

StopReason = str | None  # None — продолжать, "cutoff" — предельный год, "max_date" — данные в БД


class SpimexParser(Parser):
    """Парсер для сайта Spimex."""

    BASE_URL = "https://spimex.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; Spimex/1.0)",
        "Accept-Encoding": "gzip, deflate",
    }
    CUTOFF_YEAR = 2022
    BATCH_SIZE = 10

    def __init__(self, max_date: date | None = None) -> None:
        """Инициализирует парсер с опциональной максимальной датой."""
        self.max_date = max_date

    async def parse(self) -> list[str]:
        """Запускает парсинг и возвращает список ссылок."""
        return await self._main()

    def extract_date(self, url: str) -> date | None:
        """Извлекает дату из URL Spimex.

        Формат URL:  .../oil_20241217162000.pdf  или  .../oil_xls_20241217162000.xls
        """
        match = re.search(r"(\d{4})(\d{2})(\d{2})\d{6}", url)
        if not match:
            return None
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return date(year, month, day)

    @staticmethod
    def _parse_date_from_span(span_text: str) -> date | None:
        """Извлекает дату из текста заголовка вида 'дд.мм.гггг'."""
        try:
            return datetime.strptime(span_text.strip(), "%d.%m.%Y").date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _check_stop_reason(dt: date, max_date: date | None) -> StopReason:
        """Проверяет, нужно ли остановить парсинг и по какой причине."""
        if dt.year <= SpimexParser.CUTOFF_YEAR:
            return "cutoff"
        if max_date is not None and dt <= max_date:
            return "max_date"
        return None

    @staticmethod
    def _parse_links(html: str, max_date: date | None = None) -> tuple[list[str], StopReason]:
        """
        Парсит HTML страницы со списком бюллетеней.

        Возвращает (список ссылок, причина остановки).
        Причина остановки: None — продолжать, "cutoff" — достигнут предельный год,
        "max_date" — на странице встречена дата, уже имеющаяся в БД.
        """
        soup = BeautifulSoup(html, "lxml")
        daily_section = soup.find("div", class_="page-content__tabs__block", attrs={"data-tabcontent": "1"})
        if not daily_section:
            return [], None
        items = daily_section.find_all("div", class_="accordeon-inner__wrap-item")
        links: list[str] = []
        stop_reason: StopReason = None

        for item in items:
            title = item.find("div", class_="accordeon-inner__item-inner__title")
            if not title:
                continue
            span = title.find("span")
            if not span:
                continue

            dt = SpimexParser._parse_date_from_span(span.get_text(strip=True))
            if dt is None:
                continue

            reason = SpimexParser._check_stop_reason(dt, max_date)

            # Если год <= CUTOFF_YEAR — прерываем, дальше нет смысла
            if reason == "cutoff":
                stop_reason = "cutoff"
                break

            # Если дата уже есть в БД — пропускаем эту ссылку, но продолжаем
            # проверять остальные (могут быть более свежие)
            if reason == "max_date":
                stop_reason = "max_date"
                continue

            link = item.find("a", href=True, string=lambda text: text and "Бюллетень по итогам торгов" in text)
            if link:
                href = link.get("href")
                if isinstance(href, str):
                    links.append(urljoin(SpimexParser.BASE_URL, href))

        return links, stop_reason

    async def _fetch(self, session: aiohttp.ClientSession, url: str) -> str:
        """Загружает HTML-страницу по URL."""
        async with session.get(url) as response:
            return await response.text()

    async def _fetch_and_parse(
        self, session: aiohttp.ClientSession, url: str, max_date: date | None = None
    ) -> tuple[list[str], StopReason]:
        """Асинхронная обертка: загружает HTML и отдает парсинг в отдельный поток."""
        try:
            html = await self._fetch(session, url)
            return await asyncio.to_thread(SpimexParser._parse_links, html, max_date)
        except Exception as e:
            logger.error(f"Ошибка при обработке {url}: {e}")
            return [], None

    async def _main(self) -> list[str]:
        """
        Основная логика парсера.

        Параметры берутся из self.max_date.
        """
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit_per_host=30)
        result: list[str] = []
        seen_links: set[str] = set()
        page = 1
        max_date = self.max_date

        async with aiohttp.ClientSession(headers=self.HEADERS, timeout=timeout, connector=connector) as session:
            while True:
                urls = [
                    f"{self.BASE_URL}/markets/oil_products/trades/results/?page=page-{p}"
                    for p in range(page, page + self.BATCH_SIZE)
                ]
                logger.info(f"Загрузка пакета страниц: {page} - {page + self.BATCH_SIZE - 1}")

                stop_reason: StopReason = None
                has_new_links = False

                for url in urls:
                    links, reason = await self._fetch_and_parse(session, url, max_date)

                    if reason == "cutoff":
                        stop_reason = "cutoff"
                        break
                    elif reason == "max_date":
                        stop_reason = "max_date"
                        # Не прерываем — на следующих страницах могут быть новые даты

                    new_links = [link for link in links if link not in seen_links]
                    if new_links:
                        has_new_links = True
                        seen_links.update(new_links)
                        result.extend(new_links)

                if stop_reason == "cutoff":
                    logger.info(f"Достигнут предельный год ({self.CUTOFF_YEAR}). Завершение.")
                    break

                # Завершаемся, если на всех страницах пачки не было новых ссылок,
                # и при этом есть причина остановки (значит, зацепились за дату из БД)
                if not has_new_links and stop_reason is not None:
                    logger.info("Новые ссылки не найдены, все даты уже есть в БД. Завершение.")
                    break

                if not has_new_links:
                    logger.info("Новые ссылки не найдены.")
                    break

                page += self.BATCH_SIZE

        return result


if __name__ == "__main__":
    try:
        parser = SpimexParser()
        result = asyncio.run(parser.parse())
        logger.info(result)
    except aiohttp.ClientError as e:
        logger.error("Ошибка сети: %s", e)
