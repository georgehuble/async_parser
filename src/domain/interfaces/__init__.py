"""Содержит абстракции (интерфейсы, протоколы) для парсеров и репозиториев."""

# Re-export для обратной совместимости (старые импорты вида src.domain.interfaces.Parser)
from src.domain.interfaces.parsers import DataSource, Downloader, Parser
from src.domain.interfaces.repositories import (
    DeliveryBasisRepositoryProtocol,
    DeliveryTypeRepositoryProtocol,
    DownloadRepositoryProtocol,
    OilProductRepositoryProtocol,
    UploadRepositoryProtocol,
)

__all__ = [
    "Parser",
    "Downloader",
    "DataSource",
    "UploadRepositoryProtocol",
    "DownloadRepositoryProtocol",
    "OilProductRepositoryProtocol",
    "DeliveryBasisRepositoryProtocol",
    "DeliveryTypeRepositoryProtocol",
]
