from abc import ABC, abstractmethod


class Extract(ABC):
    """Абстрактный базовый класс для извлечения текстовых данных с загруженных файлов."""

    @abstractmethod
    async def extract(self, files: list[tuple[str, str]]) -> None:
        """Извлекает текстовые данные из файла

        Args:
            files: Список файлов (path, name).
        """
        ...
