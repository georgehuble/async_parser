import asyncio
import logging
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

BASE_URL = "https://spimex.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Spimex/1.0)",
           "Accept-Encoding": "gzip, deflate"}
CUTOFF_YEAR = 2022
BATCH_SIZE = 30


async def fetch(session: object, url: str) -> str:
    async with session.get(url) as response:
        return await response.text()


def parse_links(html: str) -> tuple[list[str], bool]:
    soup = BeautifulSoup(html, "lxml")
    daily_section = soup.find("div", class_="page-content__tabs__block", attrs={"data-tabcontent": "1"})
    if not daily_section:
        return [], False
    items = daily_section.find_all("div", class_="accordeon-inner__wrap-item")
    links = []
    for item in items:
        title = item.find("div", class_="accordeon-inner__item-inner__title")
        if title:
            span = title.find("span")
            if not span:
                continue
            try:
                year = int(span.get_text(strip=True).split(".")[-1])
            except (ValueError, IndexError):
                continue
        if year <= CUTOFF_YEAR:
            return links, True
        link = item.find("a", href=True, string=lambda text: text and "Бюллетень по итогам торгов" in text)
        if link:
            links.append(urljoin(BASE_URL, link["href"]))
    return links, False


async def fetch_and_parse(session: aiohttp.ClientSession, url: str) -> tuple[list[str], bool]:
    """Асинхронная обертка: загружает HTML и отдает парсинг в отдельный поток"""
    try:
        html = await fetch(session, url)
        return await asyncio.to_thread(parse_links, html)
    except Exception as e:
        logger.error(f"Ошибка при обработке {url}: {e}")
        return [], False


async def main() -> list[str]:
    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit_per_host=30)
    result: list[str] = []
    seen_links = set()  # Для фильтрации дубликатов
    page = 1

    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout, connector=connector) as session:
        while True:
            # Формируем пакет
            urls = [
                f"{BASE_URL}/markets/oil_products/trades/results/?page=page-{p}" for p in range(page, page + BATCH_SIZE)
                ]
            logger.info(f"Загрузка пакета страниц: {page} - {page + BATCH_SIZE - 1}")

            # Запускаем все задачи пакета
            tasks = [fetch_and_parse(session, url) for url in urls]
            batch_results = await asyncio.gather(*tasks)

            should_stop = False
            has_new_links = False

            # Обработка результатов
            for links, stop in batch_results:
                if stop:
                    should_stop = True

                new_links = [link for link in links if link not in seen_links]
                if new_links:
                    has_new_links = True
                    seen_links.update(new_links)
                    result.extend(new_links)

            if should_stop:
                logger.info("Достигнут целевой год. Завершение.")
                break

            if not has_new_links:
                logger.info("Новые ссылки не найдены (возможно, страницы закончились). Завершение.")
                break

            # Следующий пакет
            page += BATCH_SIZE

    return result


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        logger.info(result)
    except aiohttp.ClientError as e:
        logger.error("Ошибка сети: %s", e)
