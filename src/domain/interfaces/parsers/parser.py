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
