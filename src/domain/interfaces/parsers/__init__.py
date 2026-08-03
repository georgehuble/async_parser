"""Абстракции (интерфейсы) для парсеров, загрузчиков и источников данных."""

from src.domain.interfaces.parsers.datasource import DataSource
from src.domain.interfaces.parsers.downloader import Downloader
from src.domain.interfaces.parsers.fetch import Fetch
from src.domain.interfaces.parsers.parser import Parser, StopReason

__all__ = [
    "Parser",
    "Fetch",
    "StopReason",
    "Downloader",
    "DataSource",
]
