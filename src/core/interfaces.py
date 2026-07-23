"""Абстрактные базовые классы для компонентов системы."""

from abc import ABC, abstractmethod
from datetime import date


class Parser(ABC):
    """Абстрактный базовый класс для парсеров."""

    @abstractmethod
    async def parse(self) -> list[str]:
        """Запускает парсинг и возвращает список ссылок."""
        ...

    def extract_date(self, url: str) -> date | None:
        """Извлекает дату из URL парсера.

        Каждый парсер знает формат своих URL, поэтому переопределяет
        этот метод для корректного извлечения даты.
        По умолчанию возвращает None (дата не извлекается).

        Args:
            url: URL для извлечения даты.

        Returns:
            Объект date или None, если дату не удалось извлечь.
        """
        return None


class Downloader(ABC):
    """Абстрактный базовый класс для загрузчиков."""

    @abstractmethod
    async def download(self, links: list[tuple[date, str]]) -> None:
        """Загружает файлы по переданным ссылкам.

        Args:
            links: Список кортежей (дата, ссылка).
        """
        ...


class DataSource(Parser, Downloader, ABC):
    """Абстрактный базовый класс, объединяющий парсер и загрузчик.

    Представляет собой единый источник данных, который умеет
    как получать ссылки (парсинг), так и загружать файлы.
    """
    ...
