from abc import ABC, abstractmethod
from datetime import date
from enum import Enum


class StopReason(Enum):
    """Причина остановки перебора страниц при разборе HTML."""

    CONTINUE = "continue"
    CUTOFF = "cutoff"
    MAX_DATE = "max_date"


class Parser(ABC):
    """Абстрактный базовый класс для разбора HTML-страниц.

    Класс отвечает только за разбор (parse) HTML, который предоставил
    ``Fetch``. Не выполняет сетевых запросов (SRP).
    """

    @abstractmethod
    def parse_links(self, html: str, max_date: date | None = None) -> tuple[list[str], StopReason]:
        """Разбирает HTML-страницу и возвращает (ссылки, причина остановки).

        Args:
            html: HTML-содержимое страницы.
            max_date: Максимальная дата, до которой нужно собирать ссылки.

        Returns:
            Кортеж (список ссылок, причина остановки перебора страниц).
        """
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
