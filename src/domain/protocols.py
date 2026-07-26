from datetime import date
from typing import Protocol

from src.domain.entities import (
    DeliveryBasisEntity,
    DeliveryTypeEntity,
    OilProductEntity,
    TradeEntity,
)


class UploadRepositoryProtocol(Protocol):
    """Протокол репозитория для загрузки (записи) сделок в БД."""

    async def url_exists_by_date(self, dt: date) -> bool: ...

    async def add_url(self, url: str, dt: date | None = None) -> TradeEntity: ...

    async def add(
        self,
        url: str,
        dt: date | None = None,
        product_id: int | None = None,
        delivery_basis_id: int | None = None,
        delivery_type_id: int | None = None,
        volume: float | None = None,
        total: float | None = None,
        count: int | None = None,
    ) -> TradeEntity: ...


class DownloadRepositoryProtocol(Protocol):
    """Протокол репозитория для скачивания (чтения/обновления) сделок."""

    async def get_max_date(self) -> date | None: ...

    async def get_links(self) -> list[tuple[date, str]]: ...

    async def update_file_path_by_date(self, dt: date, file_path: str) -> None: ...

    async def commit(self) -> None: ...


class OilProductRepositoryProtocol(Protocol):
    """Протокол репозитория справочника нефтепродуктов."""

    async def get_or_create(
        self, exchange_product_id: str, name: str | None, oil_id: str | None
    ) -> OilProductEntity: ...

    async def get_by_id(self, product_id: int) -> OilProductEntity | None: ...


class DeliveryBasisRepositoryProtocol(Protocol):
    """Протокол репозитория справочника базисов поставки."""

    async def get_or_create(self, delivery_basis_id: str, name: str | None) -> DeliveryBasisEntity: ...

    async def get_by_id(self, basis_id: int) -> DeliveryBasisEntity | None: ...


class DeliveryTypeRepositoryProtocol(Protocol):
    """Протокол репозитория справочника типов поставки."""

    async def get_or_create(self, delivery_type_id: str) -> DeliveryTypeEntity: ...

    async def get_by_id(self, type_id: int) -> DeliveryTypeEntity | None: ...
