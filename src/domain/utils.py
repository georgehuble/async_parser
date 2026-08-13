"""Утилиты предметной области — не зависят от конкретных реализаций."""

import logging
from collections.abc import Awaitable, Callable
from datetime import date

logger = logging.getLogger(__name__)

# Тип для коллбека извлечения даты из URL
ExtractDateFn = Callable[[str], date | None]

# Тип для коллбека проверки существования записи по бизнес-ключу (exchange_id, url)
UrlExistsFn = Callable[[str, int], Awaitable[bool]]

# Тип для коллбека добавления записи (url, date, exchange_id)
AddUrlFn = Callable[[str, date | None, int], Awaitable[object]]


async def save_urls(
    url_exists: UrlExistsFn,
    add_url: AddUrlFn,
    urls: list[str],
    *,
    exchange_id: int,
    extract_date: ExtractDateFn | None = None,
) -> None:
    """Универсальная функция сохранения ссылок в БД.

    Принимает коллбеки для проверки дубликатов и добавления записи,
    а также опциональную функцию извлечения даты из URL.
    Если extract_date не передан — дата не извлекается (None).

    Дубликаты определяются по бизнес-ключу (exchange_id, url), а не по
    автоинкрементному trade_id: повторный запуск парсера не создаёт
    новые записи для уже сохранённых бюллетеней Spimex.

    Args:
        url_exists: Асинхронная функция проверки существования записи по (exchange_id, url).
        add_url: Асинхронная функция добавления ссылки (url, date, exchange_id).
        urls: Список URL для сохранения.
        exchange_id: Идентификатор биржевого источника.
        extract_date: Функция извлечения даты из URL.
    """
    saved_count = 0
    skipped_count = 0

    for url in reversed(urls):
        try:
            url_date = extract_date(url) if extract_date else None

            if await url_exists(url, exchange_id):
                skipped_count += 1
                logger.warning("Пропущен дубликат по бизнес-ключу (exchange_id=%s): %s", exchange_id, url)
                continue

            await add_url(url, url_date, exchange_id)
            saved_count += 1
            logger.info("[%d] Сохранено: %s (дата: %s)", saved_count, url, url_date)
        except Exception as e:
            logger.error("Ошибка при сохранении %s: %s", url, e)

    logger.info("Готово. Сохранено: %d, пропущено: %d", saved_count, skipped_count)
