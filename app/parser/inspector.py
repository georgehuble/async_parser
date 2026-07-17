import asyncio
import io
import ssl

import aiohttp
import pandas as pd


TEST_XLS_URL = "https://spimex.com/files/trades/result/oil_xls/oil_xls_20251204162000.xls?r=1923&p=L3VwbG9hZC9yZXBvcnRzL3BkZi9vaWwvb2lsXzIwMjUxMjA0MTYyMDAwLnBkZg"

async def inspect_xls():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        print(f"Скачиваем файл: {TEST_XLS_URL}")
        async with session.get(TEST_XLS_URL) as response:
            if response.status != 200:
                print("Ошибка скачивания!")
                return
            file_bytes = await response.read()
            print(f"Скачано байт: {len(file_bytes)}")

    file_obj = io.BytesIO(file_bytes)

    excel_file = pd.ExcelFile(file_obj)
    print(f"\n📑 Листы в документе: {excel_file.sheet_names}")

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_colwidth', 50)

    file_obj.seek(0)
    print("\n--- Первые 25 строк первого листа (сырые данные) ---")
    df_raw = pd.read_excel(file_obj, sheet_name=0, header=None)
    print(df_raw.head(25))

if __name__ == "__main__":
    asyncio.run(inspect_xls())
