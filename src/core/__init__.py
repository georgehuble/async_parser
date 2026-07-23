"""Ядро системы — только абстракции."""

from src.core.interfaces import DataSource, Downloader, Parser

__all__ = [
    "DataSource",
    "Downloader",
    "Parser",
]
