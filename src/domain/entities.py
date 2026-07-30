from dataclasses import dataclass
from datetime import datetime

from src.domain.value_objects import (
    DeliveryBasisId,
    DeliveryTypeId,
    Exchange,
    ExchangeProductId,
    Money,
    OilId,
    Volume,
)


@dataclass
class OilProductEntity:
    """Сущность нефтепродукта (справочник)."""
    id: int | None = None
    exchange: Exchange | None = None
    exchange_product_id: ExchangeProductId | None = None
    exchange_product_name: str | None = None
    oil_id: OilId | None = None


@dataclass
class DeliveryBasisEntity:
    """Сущность базиса поставки (справочник)."""
    id: int | None = None
    delivery_basis_id: DeliveryBasisId | None = None
    delivery_basis_name: str | None = None


@dataclass
class DeliveryTypeEntity:
    """Сущность типа поставки (справочник)."""
    id: int | None = None
    delivery_type_id: DeliveryTypeId | None = None


@dataclass
class TradeEntity:
    """Сущность сделки — основная запись учёта торгов."""
    id: int | None = None
    exchange: Exchange | None = None
    exchange_trade_id: str | None = None
    url: str = ""
    file_path: str | None = None
    product_id: int | None = None
    delivery_basis_id: int | None = None
    delivery_type_id: int | None = None
    volume: Volume | None = None
    total: Money | None = None
    count: int | None = None
    date: datetime | None = None
    created_on: datetime | None = None
    updated_on: datetime | None = None
