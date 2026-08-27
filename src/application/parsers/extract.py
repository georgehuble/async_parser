"""Сервис извлечения сделок: собирает файлы из папки и запускает Extract.

Принимает абстрактный Extract и путь к папке со скачанными файлами.
Сервис строит список кортежей (path, name) и передаёт его методу
Extract.extract — сам не знает, как разбирать файлы и писать в БД (SRP).
"""

import asyncio
import logging
from pathlib import Path

from src.domain.interfaces.parsers import Extract

logger = logging.getLogger(__name__)


class ExtractService:
    """Сервис: собирает файлы (path, name) из папки и извлекает из них сделки."""

    def __init__(self, extractor: Extract, files_dir: Path | str) -> None:
        """Инициализирует сервис.

        Args:
            extractor: Абстракция извлечения сделок из файлов.
            files_dir: Путь к папке со скачанными файлами (например, files/).
        """
        self._extractor = extractor
        self._files_dir = Path(files_dir)

    async def run(self) -> None:
        """Собирает файлы из папки и извлекает из них сделки в БД."""
        if not self._files_dir.is_dir():
            logger.warning("Папка с файлами не найдена: %s", self._files_dir)
            return

        # Обход дерева — синхронная работа с ФС; выполняем в потоке,
        # чтобы не блокировать event loop на больших папках
        files = await asyncio.to_thread(self._collect_files)
        logger.info("Найдено файлов для извлечения: %d", len(files))
        logger.info("Запуск извлечения %d файлов...", len(files))

        await self._extractor.extract(files)

    def _collect_files(self) -> list[tuple[str, str]]:
        """Собирает (path, name) не-скрытых файлов из папки (рекурсивно).

        Returns:
            Список кортежей (путь к файлу, имя файла).
        """
        # Скрытые файлы (например, .gitkeep) не являются бюллетенями и пропускаются
        return [
            (str(file_path), file_path.name)
            for file_path in sorted(self._files_dir.rglob("*"))
            if file_path.is_file() and not file_path.name.startswith(".")
        ]

