"""Абстракции (интерфейсы) для парсеров, загрузчиков и источников данных."""

from src.domain.interfaces.parsers.datasource import DataSource
from src.domain.interfaces.parsers.downloader import Downloader
from src.domain.interfaces.parsers.parser import Parser

__all__ = [
    "Parser",
    "Downloader",
    "DataSource",
]
