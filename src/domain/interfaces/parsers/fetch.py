from abc import ABC, abstractmethod
from datetime import date


class Fetch(ABC):
    """Абстракция обхода сайта и сбора ссылок.

    Конкретные реализации знают, как построить URL пагинации и скачать
    страницы. Разбор HTML они делегируют абстракции ``Parser``.
    """

    @abstractmethod
    async def collect_links(self, max_date: date | None = None) -> list[str]:
        """Обходит страницы сайта и возвращает список ссылок.

        Args:
            max_date: Максимальная дата для ранней остановки обхода.

        Returns:
            Список собранных ссылок.
        """
        ...
