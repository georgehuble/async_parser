"""Абстрактные базовые классы для компонентов системы."""

from abc import ABC, abstractmethod
from datetime import date


class Parser(ABC):
    """Абстрактный базовый класс для парсеров."""

    @abstractmethod
    async def parse(self) -> list[str]:
        """Запускает парсинг и возвращает список ссылок."""
        ...


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
