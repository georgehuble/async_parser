from abc import ABC, abstractmethod
from datetime import date

from src.domain.entities import (
    DeliveryBasisEntity,
    DeliveryTypeEntity,
    ExchangeEntity,
    OilProductEntity,
    TradeEntity,
)


class ExchangeRepositoryAbstract(ABC):
    """Абстрактный базовый класс репозитория биржевых источников."""

    @abstractmethod
    async def get_id_by_name(self, name: str) -> int | None: ...

    @abstractmethod
    async def get_or_create_by_name(self, name: str) -> ExchangeEntity: ...


class UploadRepositoryAbstract(ABC):
    """Абстрактный базовый класс репозитория для загрузки (записи) сделок в БД."""

    @abstractmethod
    async def url_exists(self, url: str, exchange_id: int) -> bool: ...

    @abstractmethod
    async def add_url(self, url: str, dt: date | None = None, exchange_id: int = 0) -> TradeEntity: ...

    @abstractmethod
    async def add(
        self,
        url: str,
        dt: date | None = None,
        exchange_id: int = 0,
        exchange_trade_id: str | None = None,
        product_id: int | None = None,
        delivery_basis_id: str | None = None,
        delivery_type_id: str | None = None,
        volume: float | None = None,
        total: float | None = None,
        count: int | None = None,
        file_path: str | None = None,
    ) -> TradeEntity: ...

    @abstractmethod
    async def add_trades(self, trades: list[TradeEntity]) -> None:
        """Массово добавляет сделки без проверки существования по бизнес-ключу.

        Вызывающий код обязан отфильтровать уже существующие сделки
        (например, через ``get_existing_trade_ids``).
        """
        ...


class DownloadRepositoryAbstract(ABC):
    """Абстрактный базовый класс репозитория для скачивания (чтения/обновления) сделок."""

    @abstractmethod
    async def get_max_date(self) -> date | None: ...

    @abstractmethod
    async def get_links(self) -> list[tuple[date, str, int]]: ...

    @abstractmethod
    async def get_bulletin_url_by_date(self, dt: date, exchange_id: int) -> str | None: ...

    @abstractmethod
    async def get_existing_trade_ids(self, exchange_id: int, trade_ids: list[str]) -> set[str]:
        """Возвращает exchange_trade_id уже существующих сделок (для пропуска дубликатов)."""

    @abstractmethod
    async def update_file_path_by_url(self, url: str, exchange_id: int, file_path: str) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...


class OilProductRepositoryAbstract(ABC):
    """Абстрактный базовый класс репозитория справочника нефтепродуктов."""

    @abstractmethod
    async def get_or_create(
        self,
        exchange_product_id: str,
        name: str | None,
        oil_id: str | None,
        exchange_id: int,
    ) -> OilProductEntity: ...

    @abstractmethod
    async def get_by_id(self, product_id: int) -> OilProductEntity | None: ...


class DeliveryBasisRepositoryAbstract(ABC):
    """Абстрактный базовый класс репозитория справочника базисов поставки."""

    @abstractmethod
    async def get_or_create(self, delivery_basis_id: str, name: str | None) -> DeliveryBasisEntity: ...

    @abstractmethod
    async def get_by_id(self, basis_id: str) -> DeliveryBasisEntity | None: ...


class DeliveryTypeRepositoryAbstract(ABC):
    """Абстрактный базовый класс репозитория справочника типов поставки."""

    @abstractmethod
    async def get_or_create(self, delivery_type_id: str) -> DeliveryTypeEntity: ...

    @abstractmethod
    async def get_by_id(self, type_id: str) -> DeliveryTypeEntity | None: ...


class TradeRepositoryAbstract(
    UploadRepositoryAbstract,
    DownloadRepositoryAbstract,
):
    """Абстрактный базовый класс репозитория trade — объединяет запись и чтение."""
