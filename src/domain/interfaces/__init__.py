"""Содержит абстракции (интерфейсы, протоколы) для парсеров и репозиториев."""

# Re-export для обратной совместимости (старые импорты вида src.domain.interfaces.Parser)
from src.domain.interfaces.parsers import Downloader, Parser
from src.domain.interfaces.repositories import (
    DeliveryBasisRepositoryAbstract,
    DeliveryTypeRepositoryAbstract,
    DownloadRepositoryAbstract,
    OilProductRepositoryAbstract,
    UploadRepositoryAbstract,
)

__all__ = [
    "Parser",
    "Downloader",
    "UploadRepositoryAbstract",
    "DownloadRepositoryAbstract",
    "OilProductRepositoryAbstract",
    "DeliveryBasisRepositoryAbstract",
    "DeliveryTypeRepositoryAbstract",
]
