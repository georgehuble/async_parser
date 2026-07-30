from abc import ABC, abstractmethod
from datetime import date


class DataSource(ABC):
    """Абстрактный источник данных — композиция парсера и загрузчика."""

    @abstractmethod
    async def parse(self) -> list[str]:
        """Запускает парсинг и возвращает список ссылок."""
        ...

    @abstractmethod
    async def download(self, links: list[tuple[date, str]]) -> None:
        """Загружает файлы по переданным ссылкам."""
        ...
