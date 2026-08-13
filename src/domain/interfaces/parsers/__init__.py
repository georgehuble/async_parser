"""Абстракции (интерфейсы) для парсеров и загрузчиков."""

from src.domain.interfaces.parsers.downloader import Downloader
from src.domain.interfaces.parsers.fetch import Fetch
from src.domain.interfaces.parsers.parser import Parser, StopReason

__all__ = [
    "Parser",
    "Fetch",
    "StopReason",
    "Downloader",
]
