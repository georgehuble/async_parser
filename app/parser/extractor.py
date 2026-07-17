import asyncio
import io
import ssl

import aiohttp
import pandas as pd

TEST_XLS_URL = "https://spimex.com/files/trades/result/oil_xls/oil_xls_20251204162000.xls?r=1923&p=L3VwbG9hZC9yZXBvcnRzL3BkZi9vaWwvb2lsXzIwMjUxMjA0MTYyMDAwLnBkZg"

def extract_data_from_xls(file_bytes: bytes) -> pd.DataFrame:

    file_obj = io.BytesIO(file_bytes)

    df_raw = pd.read_excel(file_obj, sheet_name=0, header=None)

    metric_ton_row = None
    for idx, row in df_raw.iterrows():
        cell_value = str(row[1]) if pd.notna(row[1]) else ""
        if "Метрическая тонна" in cell_value:
            metric_ton_row = idx
            break

    if metric_ton_row is None:
        print("Таблица 'Метрическая тонна' не найдена!")
        return pd.DataFrame()

    print(f"Найдена таблица 'Метрическая тонна' на строке {metric_ton_row}")

    header_row = metric_ton_row + 1
    data_start_row = metric_ton_row + 3

    df = pd.read_excel(file_obj, sheet_name=0, header=header_row)

    required_columns = [
        'Код\nИнструмента',
        'Наименование\nИнструмента',
        'Базис\nпоставки',
        'Объем\nДоговоров\nв единицах\nизмерения',
        'Обьем\nДоговоров,\nруб.',  # Опечатка в оригинале!
        'Количество\nДоговоров,\nшт.'
    ]

    # Проверяем, что все столбцы есть
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        print(f"Отсутствуют столбцы: {missing_cols}")
        print(f"Доступные столбцы: {list(df.columns)}")
        return pd.DataFrame()

    df = df[required_columns].copy()

    df.columns = [
        'exchange_product_id',
        'exchange_product_name',
        'delivery_basis_name',
        'volume',
        'total',
        'count'
    ]

    df = df.dropna(subset=['exchange_product_id'])
    df = df[~df['exchange_product_id'].astype(str).str.contains('Итого', na=False)]

    df['count'] = pd.to_numeric(df['count'], errors='coerce')
    df = df[df['count'] > 0]

    # 10. Приводим типы данных
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    df['total'] = pd.to_numeric(df['total'], errors='coerce')
    df['count'] = df['count'].astype(int)

    print(f"Извлечено строк: {len(df)}")
    return df


async def test_extractor():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        print("Скачиваем файл...")
        async with session.get(TEST_XLS_URL) as response:
            if response.status != 200:
                print("Ошибка скачивания!")
                return
            file_bytes = await response.read()

    df = await extract_data_from_xls(file_bytes)

    if not df.empty:
        print("\n--- Первые 10 строк извлеченных данных ---")
        print(df.head(10))
        print("\n--- Типы данных ---")
        print(df.dtypes)


if __name__ == "__main__":
    asyncio.run(test_extractor())
