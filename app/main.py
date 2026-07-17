import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import async_session_factory
from parser.downloader import download_all_files
from parser.fetcher import get_xls_links
from saver import check_database_stats, save_to_database


async def main():
    """
    Главный оркестратор: собирает ссылки, скачивает файлы, сохраняет в БД.
    """
    print("=" * 80)
    print("ЗАПУСК ПАРСЕРА ИТОГОВ ТОРГОВ СПБМТСБ")
    print("=" * 80)

    print("\nЭТАП 1: Сбор ссылок на бюллетени...")
    links = await get_xls_links(batch_size=10, max_concurrent=5)

    xls_links = [link for link in links if link['format'] == 'xls']
    pdf_links = [link for link in links if link['format'] == 'pdf']

    print("\nСтатистика ссылок:")
    print(f"   - Всего уникальных ссылок: {len(links)}")
    print(f"   - XLS-файлов (обрабатываем): {len(xls_links)}")
    print(f"   - PDF-файлов (пропускаем): {len(pdf_links)}")

    if not xls_links:
        print("Не найдено XLS-файлов для обработки!")
        return


    print("\nЭТАП 2: Скачивание и обработка XLS-файлов...")
    df = await download_all_files(xls_links, max_concurrent=10)

    if df.empty:
        print("Не удалось извлечь данные ни из одного файла!")
        return

    print("\nУспешно обработано файлов!")
    print(f"Итого строк для сохранения: {len(df)}")
    print(f"Период данных: с {df['date'].min()} по {df['date'].max()}")

    print("\nЭТАП 3: Сохранение в PostgreSQL...")
    async with async_session_factory() as session:
        saved_count = await save_to_database(df, session)

        print("\nЭТАП 4: Проверка статистики БД...")
        stats = await check_database_stats(session)
        print(f"   - Всего записей в БД: {stats['total_records']}")
        print(f"   - Период в БД: с {stats['date_range']['min']} по {stats['date_range']['max']}")

    print("\n" + "=" * 80)
    print(f"ПАРСИНГ ЗАВЕРШЕН УСПЕШНО! Сохранено {saved_count} записей.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
