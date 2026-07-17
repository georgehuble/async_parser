import asyncio
import re
import ssl
from datetime import datetime
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

BASE_URL = "https://spimex.com/markets/oil_products/trades/results/"
PAGINATION_URL = BASE_URL + "?page=page-{}"

DATE_PATTERN = re.compile(r'oil(?:_xls)?_(\d{8})')


async def fetch_page(
    session: aiohttp.ClientSession,
    url: str,
    semaphore: asyncio.Semaphore) -> tuple[list[dict], bool]:

    async with semaphore:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Ошибка {response.status} для {url}")
                    return [], False

                html = await response.text()
        except Exception as e:
            print(f"Исключение при запросе {url}: {e}")
            return [], False

    soup = BeautifulSoup(html, "html.parser")

    xls_links = soup.find_all("a", class_="xls") + soup.find_all("a", class_="pdf")

    found_links = []
    reached_2022 = False

    for link_tag in xls_links:
        href = link_tag.get("href", "")
        if not href:
            continue

        absolute_url = urljoin(BASE_URL, href)

        match = DATE_PATTERN.search(href)
        if not match:
            continue

        date_str = match.group(1)

        try:
            file_date = datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            continue

        if file_date.year < 2023:
            reached_2022 = True
            continue

        found_links.append({
            "date": file_date,
            "url": absolute_url,
            "format": "xls" if ".xls" in href else "pdf"
        })

    return found_links, reached_2022


async def get_xls_links(batch_size: int = 10, max_concurrent: int = 5) -> list[dict]:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    connector = aiohttp.TCPConnector(ssl=ssl_context)

    semaphore = asyncio.Semaphore(max_concurrent)

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }

    all_links = []
    page = 1

    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        while True:
            urls = []
            for i in range(batch_size):
                if page == 1 and i == 0:
                    urls.append(BASE_URL)
                else:
                    urls.append(PAGINATION_URL.format(page - 1 + i))

            print(f"Запрашиваем пачку страниц: {page} - {page + batch_size - 1}")

            tasks = [
                fetch_page(session, url, semaphore)
                for url in urls
            ]

            results = await asyncio.gather(*tasks)

            stop_parsing = False
            for links, is_too_old in results:
                all_links.extend(links)
                if is_too_old:
                    stop_parsing = True

            if stop_parsing:
                print("Достигнут 2022 год. Сбор завершен.")
                break

            page += batch_size

    all_links.sort(key=lambda x: x["date"], reverse=True)

    unique_links = {}
    for link in all_links:
        if link["date"] not in unique_links:
            unique_links[link["date"]] = link

    all_links = list(unique_links.values())

    print(f"\n Итого собрано ссылок: {len(all_links)}")
    if all_links:
        print(f"Самая свежая: {all_links[0]['date']}")
        print(f"Самая старая: {all_links[-1]['date']}")

    xls_count = sum(1 for link in all_links if link["format"] == "xls")
    pdf_count = sum(1 for link in all_links if link["format"] == "pdf")
    print(f"XLS: {xls_count}, PDF: {pdf_count}")


    return all_links


if __name__ == "__main__":
    links = asyncio.run(get_xls_links(batch_size=5, max_concurrent=3))
    print("\nПервые 5 ссылок:")
    for link in links[:5]:
        print(link)
