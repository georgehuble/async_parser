import asyncio
import ssl
import random

import aiohttp
import pandas as pd

from app.parser.extractor import extract_data_from_xls


BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://spimex.com/markets/oil_products/trades/results/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin"
}


async def download_and_process_file(
    session: aiohttp.ClientSession,
    file_info: dict,
    semaphore: asyncio.Semaphore
) -> pd.DataFrame:

    file_bytes = None

    for attempt in range(4):
        async with semaphore:
            try:
                jitter = random.uniform(2.0, 5.0)
                await asyncio.sleep(jitter)

                async with session.get(file_info['url'], headers=BROWSER_HEADERS) as response:
                    if response.status == 200:
                        file_bytes = await response.read()
                        break
                    elif response.status == 503 or response.status == 429:
                        wait_time = 30 * (2 ** attempt)
                        print(f"503/429 (WAF защита) для {file_info['date']}. IP в кулдауне. Ждем {wait_time}с... (Попытка {attempt+1}/4)")
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"Ошибка {response.status} для {file_info['url']}")
                        return pd.DataFrame()
            except Exception as e:
                print(f"Исключение при скачивании {file_info['url']}: {e}")
                await asyncio.sleep(10)

    if file_bytes is None:
        print(f"Не удалось скачать файл за {file_info['date']} (IP заблокирован надолго).")
        return pd.DataFrame()

    df = await asyncio.to_thread(extract_data_from_xls, file_bytes)

    if df.empty:
        return df

    df['date'] = file_info['date']
    df['oil_id'] = df['exchange_product_id'].str[:4]
    df['delivery_basis_id'] = df['exchange_product_id'].str[4:7]
    df['delivery_type_id'] = df['exchange_product_id'].str[-1]

    return df


async def download_all_files(
    links: list[dict],
    max_concurrent: int = 1
) -> pd.DataFrame:

    xls_links = [link for link in links if link['format'] == 'xls']
    print(f"Будет скачано XLS-файлов: {len(xls_links)}")
    print("Включен 'Вежливый режим'. Скачивание займет время, но мы избежим бана.")

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    semaphore = asyncio.Semaphore(max_concurrent)
    all_dataframes = []

    async with aiohttp.ClientSession(connector=connector, headers=BROWSER_HEADERS) as session:
        tasks = [
            download_and_process_file(session, link, semaphore)
            for link in xls_links
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, pd.DataFrame) and not result.empty:
                all_dataframes.append(result)

    if not all_dataframes:
        print("Не удалось извлечь данные ни из одного файла!")
        return pd.DataFrame()

    final_df = pd.concat(all_dataframes, ignore_index=True)
    print(f"Итого строк в финальном DataFrame: {len(final_df)}")
    return final_df


if __name__ == "__main__":
    from app.parser.fetcher import get_xls_links

    async def run_full_download():
        print("Начинаем полный сбор данных (Вежливый режим)...\n")

        links = await get_xls_links(batch_size=10, max_concurrent=3)
        xls_links = [link for link in links if link['format'] == 'xls']

        df = await download_all_files(xls_links, max_concurrent=1)

        if not df.empty:
            print("\nУспешно обработано файлов!")
            print(f"Итого строк: {len(df)}")
            print(f"Период: с {df['date'].min()} по {df['date'].max()}")
            df.to_csv('spimex_data.csv', index=False)
            print("Данные сохранены в spimex_data.csv")

    asyncio.run(run_full_download())
