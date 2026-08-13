"""Тесты save_urls: дубликаты определяются по бизнес-ключу (exchange_id, url)."""

import asyncio
from datetime import date

from src.domain.utils import save_urls


def test_save_urls_skips_duplicate_by_business_key() -> None:
    """Повторная ссылка пропускается: идентификация идёт по url, а не по автоинкрементному ID."""
    existing_urls = {"https://spimex.example/oil_20240101120000.pdf"}
    added: list[tuple[str, date | None]] = []

    async def url_exists(url: str, exchange_id: int) -> bool:
        assert exchange_id == 1
        return url in existing_urls

    async def add_url(url: str, dt: date | None, exchange_id: int) -> None:
        added.append((url, dt))

    asyncio.run(
        save_urls(
            url_exists=url_exists,
            add_url=add_url,
            urls=[
                "https://spimex.example/oil_20240101120000.pdf",
                "https://spimex.example/oil_20240102120000.pdf",
            ],
            exchange_id=1,
            extract_date=lambda url: date(2024, 1, 1),
        )
    )

    assert added == [("https://spimex.example/oil_20240102120000.pdf", date(2024, 1, 1))]


def test_save_urls_keeps_new_links() -> None:
    """Если записей в БД нет — все ссылки сохраняются с извлечённой датой."""
    added: list[tuple[str, date | None]] = []

    async def url_exists(url: str, exchange_id: int) -> bool:
        return False

    async def add_url(url: str, dt: date | None, exchange_id: int) -> None:
        added.append((url, dt))

    url = "https://spimex.example/oil_20240101120000.pdf"
    asyncio.run(
        save_urls(
            url_exists=url_exists,
            add_url=add_url,
            urls=[url],
            exchange_id=1,
            extract_date=lambda _: date(2024, 1, 1),
        )
    )

    assert added == [(url, date(2024, 1, 1))]
