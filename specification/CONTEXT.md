# Контекст проекта (AS-IS)

Актуальное описание системы. Обновляется, когда меняется архитектура.

## Назначение

`async_parser` — асинхронный парсер бюллетеней торгов с сайта СПбМТСБ (SPIMEX):
собирает ссылки на бюллетени, скачивает файлы (XLS/PDF), разбирает сделки
и сохраняет их в PostgreSQL.

## Технологический стек

- Python 3.11, `asyncio`
- `aiohttp` — HTTP-запросы
- `BeautifulSoup` + `lxml` — разбор HTML и XLS
- `SQLAlchemy 2.0` (async) + `asyncpg` + PostgreSQL
- `Alembic` — миграции
- `pydantic-settings` — конфигурация

## Архитектурные слои

| Слой        | Путь                       | Назначение                                 |
| ----------- | -------------------------- | ------------------------------------------ |
| domain      | `src/domain/`              | Сущности, value objects, ABC-интерфейсы    |
| application | `src/application/`         | Fetch, Parser, Downloader, UploadService   |
| infra       | `src/infra/database/`      | Модели, сессия, репозитории                |
| main        | `src/main.py`              | Ручная сборка DI и `Orchestrator`          |

## Поток данных

1. `Orchestrator` получает `max_date` из БД (максимальная дата по бюллетеням).
2. `SpimexFetch` перебирает страницы пагинации и скачивает HTML.
3. `SpimexParser` разбирает HTML: извлекает ссылки на бюллетени и определяет
   `StopReason` (`CUTOFF` — год <= `CUTOFF_YEAR`; `MAX_DATE` — дата <= `max_date`).
4. `UploadService` сохраняет новые ссылки в `trades` (строки-«бюллетени» без
   `exchange_trade_id`), бизнес-ключ `(exchange_id, url)`.
5. `TradeRepository.get_links()` возвращает ссылки без `file_path`.
6. `SpimexDownloader` скачивает файлы и обновляет `file_path` по
   `(exchange_id, url)`.
7. Повторный запуск пропускает уже скачанные бюллетени.

## Модель данных

| Таблица          | Назначение                                | Ключ                                  |
| ---------------- | ----------------------------------------- | ------------------------------------- |
| `exchanges`      | Справочник бирж                           | `exchange_id` (суррогатный)           |
| `oil_products`   | Справочник нефтепродуктов                 | `product_id`; уникальность `(exchange_id, exchange_product_id)` |
| `delivery_bases` | Справочник базисов поставки               | `delivery_basis_id` (код)             |
| `delivery_types` | Справочник типов поставки                 | `delivery_type_id` (код)              |
| `trades`         | Бюллетени и сделки                        | `trade_id`; бизнес-ключи см. ниже     |

Бизнес-ключи таблицы `trades`:

- бюллетень: `(exchange_id, url)` — уникален для строк без `exchange_trade_id`
  (частичный уникальный индекс `uix_exchange_url`);
- сделка: `(exchange_id, exchange_trade_id)` — индекс `uix_exchange_trade`.

## Известные TODO

- Модель Pub/Sub с `asyncio.Queue` для разбиения пайплайна на независимые шаги
  (см. `TODO.md` и пример `specs/001-pipeline-queue.md`).
- UML-диаграммы БД.
