"""Протоколы репозиториев для работы с БД."""

from src.domain.interfaces.repositories.protocols import (
    DeliveryBasisRepositoryProtocol,
    DeliveryTypeRepositoryProtocol,
    DownloadRepositoryProtocol,
    OilProductRepositoryProtocol,
    UploadRepositoryProtocol,
)

__all__ = [
    "UploadRepositoryProtocol",
    "DownloadRepositoryProtocol",
    "OilProductRepositoryProtocol",
    "DeliveryBasisRepositoryProtocol",
    "DeliveryTypeRepositoryProtocol",
]
