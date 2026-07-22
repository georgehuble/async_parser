import asyncio
import logging

from sqlalchemy.exc import IntegrityError

from database import Spimex, get_session
from parser.spimex import main as run_spimex_parser

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def save_urls(urls: list[str]):
    """
    Последовательно в обратном порядке сохраняет URL в БД.
    Каждая запись коммитится отдельно, чтобы корректно обрабатывать дубликаты.
    """
    logger.info(f"Начало сохранения {len(urls)} ссылок в БД...")
    saved_count = 0
    skipped_count = 0

    for url in reversed(urls):
        # Для каждой записи — своя сессия, чтобы commit/rollback
        # работали независимо и не ломали весь цикл
        async with get_session() as session:
            try:
                new_record = Spimex(url=url)
                session.add(new_record)
                await session.commit()  # Коммитим каждую запись отдельно
                saved_count += 1
                logger.info(f"[{saved_count}] Сохранено: {url}")
            except IntegrityError:
                await session.rollback()
                skipped_count += 1
                logger.warning(f"Пропущен дубликат: {url}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка при сохранении {url}: {e}")

    logger.info(
        f"Готово. Сохранено: {saved_count}, пропущено: {skipped_count}"
    )


async def main():
    try:
        logger.info("Запуск парсера Spimex...")
        scraped_urls = await run_spimex_parser()

        if not scraped_urls:
            logger.info("Ссылки не найдены. Завершение работы.")
            return

        logger.info(f"Парсер нашел {len(scraped_urls)} уникальных ссылок.")
        await save_urls(scraped_urls)

    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
