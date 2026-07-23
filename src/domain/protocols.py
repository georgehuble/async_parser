from datetime import date
from typing import Protocol

from src.domain.entities import ExchangeRecord


class UploadRepositoryProtocol(Protocol):
    """Протокол репозитория для загрузки (записи) ссылок в БД."""

    async def get_max_date(self) -> date | None: ...

    async def url_exists_by_date(self, date: date) -> bool: ...

    async def add_url(self, url: str, date: date | None = None) -> ExchangeRecord: ...


class DownloadRepositoryProtocol(Protocol):
    """Протокол репозитория для скачивания (чтения/обновления) файлов."""

    async def get_links(self) -> list[tuple[date, str]]: ...

    async def update_file_path_by_date(self, dt: date, file_path: str) -> None: ...

    async def commit(self) -> None: ...
