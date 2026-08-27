from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.domain.value_objects import (
    DeliveryBasisId,
    DeliveryTypeId,
    ExchangeProductId,
    Money,
    OilId,
    Volume,
)


@dataclass
class ExchangeEntity:
    """Сущность биржевого источника (справочник)."""
    exchange_id: int | None = None
    name: str | None = None


@dataclass
class OilProductEntity:
    """Сущность нефтепродукта (справочник)."""
    product_id: int | None = None
    exchange_id: int | None = None
    exchange_product_id: ExchangeProductId | None = None
    exchange_product_name: str | None = None
    oil_id: OilId | None = None


@dataclass
class DeliveryBasisEntity:
    """Сущность базиса поставки (справочник).

    Первичный ключ — бизнес-код `delivery_basis_id` (например 'NAS').
    """
    delivery_basis_id: DeliveryBasisId | None = None
    delivery_basis_name: str | None = None


@dataclass
class DeliveryTypeEntity:
    """Сущность типа поставки (справочник).

    Первичный ключ — бизнес-код `delivery_type_id` (например 'G').
    """
    delivery_type_id: DeliveryTypeId | None = None


@dataclass
class TradeEntity:
    """Сущность сделки — основная запись учёта торгов."""
    trade_id: int | None = None
    exchange_id: int | None = None
    exchange_trade_id: str | None = None
    url: str = ""
    file_path: str | None = None
    product_id: int | None = None
    exchange_product_id: str | None = None
    exchange_product_name: str | None = None
    oil_id: str | None = None
    delivery_basis_id: str | None = None
    delivery_basis_name: str | None = None
    delivery_type_id: str | None = None
    volume: Volume | None = None
    total: Money | None = None
    count: int | None = None
    date: date | None = None
    created_on: datetime | None = None
    updated_on: datetime | None = None
