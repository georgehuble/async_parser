"""Абстракции репозиториев для работы с БД."""

from src.domain.interfaces.repositories.abstracts import (
    DeliveryBasisRepositoryAbstract,
    DeliveryTypeRepositoryAbstract,
    DownloadRepositoryAbstract,
    ExchangeRepositoryAbstract,
    OilProductRepositoryAbstract,
    TradeRepositoryAbstract,
    UploadRepositoryAbstract,
)

__all__ = [
    "UploadRepositoryAbstract",
    "DownloadRepositoryAbstract",
    "ExchangeRepositoryAbstract",
    "OilProductRepositoryAbstract",
    "DeliveryBasisRepositoryAbstract",
    "DeliveryTypeRepositoryAbstract",
    "TradeRepositoryAbstract",
]
