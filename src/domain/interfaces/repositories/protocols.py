from abc import ABC, abstractmethod
from datetime import date

from src.domain.entities import (
    DeliveryBasisEntity,
    DeliveryTypeEntity,
    OilProductEntity,
    TradeEntity,
)


class UploadRepositoryProtocol(ABC):
    """Абстрактный базовый класс репозитория для загрузки (записи) сделок в БД."""

    @abstractmethod
    async def url_exists_by_date(self, dt: date, exchange: str | None = None) -> bool: ...

    @abstractmethod
    async def add_url(self, url: str, dt: date | None = None, exchange: str | None = None) -> TradeEntity: ...

    @abstractmethod
    async def add(
        self,
        url: str,
        dt: date | None = None,
        exchange: str | None = None,
        exchange_trade_id: str | None = None,
        product_id: int | None = None,
        delivery_basis_id: int | None = None,
        delivery_type_id: int | None = None,
        volume: float | None = None,
        total: float | None = None,
        count: int | None = None,
    ) -> TradeEntity: ...


class DownloadRepositoryProtocol(ABC):
    """Абстрактный базовый класс репозитория для скачивания (чтения/обновления) сделок."""

    @abstractmethod
    async def get_max_date(self) -> date | None: ...

    @abstractmethod
    async def get_links(self) -> list[tuple[date, str]]: ...

    @abstractmethod
    async def update_file_path_by_date(self, dt: date, file_path: str) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...


class OilProductRepositoryProtocol(ABC):
    """Абстрактный базовый класс репозитория справочника нефтепродуктов."""

    @abstractmethod
    async def get_or_create(
        self,
        exchange_product_id: str,
        name: str | None,
        oil_id: str | None,
        exchange: str | None = None,
    ) -> OilProductEntity: ...

    @abstractmethod
    async def get_by_id(self, product_id: int) -> OilProductEntity | None: ...


class DeliveryBasisRepositoryProtocol(ABC):
    """Абстрактный базовый класс репозитория справочника базисов поставки."""

    @abstractmethod
    async def get_or_create(self, delivery_basis_id: str, name: str | None) -> DeliveryBasisEntity: ...

    @abstractmethod
    async def get_by_id(self, basis_id: int) -> DeliveryBasisEntity | None: ...


class DeliveryTypeRepositoryProtocol(ABC):
    """Абстрактный базовый класс репозитория справочника типов поставки."""

    @abstractmethod
    async def get_or_create(self, delivery_type_id: str) -> DeliveryTypeEntity: ...

    @abstractmethod
    async def get_by_id(self, type_id: int) -> DeliveryTypeEntity | None: ...


class TradeRepositoryProtocol(
    UploadRepositoryProtocol,
    DownloadRepositoryProtocol,
):
    """Абстрактный базовый класс репозитория trade — объединяет запись и чтение."""
