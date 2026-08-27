"""Тесты ExtractService: сбор файлов (path, name) из папки и передача в Extract."""

import asyncio
from pathlib import Path

from src.application.parsers.extract import ExtractService
from src.domain.interfaces.parsers import Extract


class FakeExtract(Extract):
    """Экстрактор, запоминающий переданный список файлов."""

    def __init__(self) -> None:
        self.files: list[tuple[str, str]] = []

    async def extract(self, files: list[tuple[str, str]]) -> None:
        self.files.extend(files)


def test_extract_service_collects_files_recursively(tmp_path: Path) -> None:
    """Сервис собирает все файлы из папки (рекурсивно) в кортежи (path, name)."""
    (tmp_path / "pdf").mkdir()
    (tmp_path / "xls").mkdir()
    pdf = tmp_path / "pdf" / "2023-01-12.pdf"
    pdf.write_bytes(b"%PDF-1.5 fake")
    xls = tmp_path / "xls" / "2023-01-12.xls"
    xls.write_bytes(b"xls content")
    (tmp_path / "other").mkdir()

    fake = FakeExtract()
    service = ExtractService(extractor=fake, files_dir=tmp_path)
    asyncio.run(service.run())

    assert sorted(fake.files) == sorted([(str(pdf), "2023-01-12.pdf"), (str(xls), "2023-01-12.xls")])


def test_extract_service_missing_dir_skips(tmp_path: Path) -> None:
    """Если папки нет — extract не вызывается и ничего не делается."""
    fake = FakeExtract()
    service = ExtractService(extractor=fake, files_dir=tmp_path / "not_exists")
    asyncio.run(service.run())

    assert fake.files == []


def test_extract_service_skips_hidden_files(tmp_path: Path) -> None:
    """Скрытые файлы (например, .gitkeep) не попадают в список на извлечение."""
    pdf = tmp_path / "2023-01-12.pdf"
    pdf.write_bytes(b"%PDF-1.5 fake")
    (tmp_path / ".gitkeep").write_bytes(b"")

    fake = FakeExtract()
    service = ExtractService(extractor=fake, files_dir=tmp_path)
    asyncio.run(service.run())

    assert fake.files == [(str(pdf), "2023-01-12.pdf")]
