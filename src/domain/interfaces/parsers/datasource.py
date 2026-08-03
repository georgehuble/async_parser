from abc import ABC, abstractmethod
from datetime import date


class DataSource(ABC):
    """Абстракция источника данных: получение ссылок и скачивание файлов."""

    @abstractmethod
    async def parse(self) -> list[str]:
        """Возвращает список ссылок на файлы."""
        ...

    @abstractmethod
    async def download(self, links: list[tuple[date, str]]) -> None:
        """Загружает файлы по переданным ссылкам.

        Args:
            links: Список кортежей (дата, ссылка).
        """
        ...
