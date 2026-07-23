"""Утилиты предметной области — не зависят от конкретных реализаций."""

import logging
from collections.abc import Awaitable, Callable
from datetime import date

logger = logging.getLogger(__name__)

# Тип для коллбека извлечения даты из URL
ExtractDateFn = Callable[[str], date | None]


async def save_urls(
    url_exists_by_date: Callable[[date], Awaitable[bool]],
    add_url: Callable[[str, date | None], Awaitable[object]],
    urls: list[str],
    *,
    extract_date: ExtractDateFn | None = None,
) -> None:
    """Универсальная функция сохранения ссылок в БД.

    Принимает коллбеки для проверки дубликатов и добавления записи,
    а также опциональную функцию извлечения даты из URL.
    Если extract_date не передан — дата не извлекается (None).

    Args:
        url_exists_by_date: Асинхронная функция проверки существования даты.
        add_url: Асинхронная функция добавления ссылки.
        urls: Список URL для сохранения.
        extract_date: Функция извлечения даты из URL.
    """
    saved_count = 0
    skipped_count = 0

    for url in reversed(urls):
        try:
            url_date = extract_date(url) if extract_date else None

            if url_date is not None and await url_exists_by_date(url_date):
                skipped_count += 1
                logger.warning("Пропущен дубликат по дате %s: %s", url_date, url)
                continue

            await add_url(url, url_date)
            saved_count += 1
            logger.info("[%d] Сохранено: %s (дата: %s)", saved_count, url, url_date)
        except Exception as e:
            logger.error("Ошибка при сохранении %s: %s", url, e)

    logger.info("Готово. Сохранено: %d, пропущено: %d", saved_count, skipped_count)
