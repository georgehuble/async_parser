from abc import ABC, abstractmethod
from datetime import date


class Downloader(ABC):
    """Абстрактный базовый класс для загрузчиков."""

    @abstractmethod
    async def download(self, links: list[tuple[date, str]]) -> None:
        """Загружает файлы по переданным ссылкам.

        Args:
            links: Список кортежей (дата, ссылка).
        """
        ...
