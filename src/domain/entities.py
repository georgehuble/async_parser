from dataclasses import dataclass
from datetime import datetime


@dataclass
class OilProductEntity:
    """Сущность нефтепродукта (справочник)."""
    id: int | None = None
    exchange_product_id: str = ""
    exchange_product_name: str | None = None
    oil_id: str | None = None


@dataclass
class DeliveryBasisEntity:
    """Сущность базиса поставки (справочник)."""
    id: int | None = None
    delivery_basis_id: str = ""
    delivery_basis_name: str | None = None


@dataclass
class DeliveryTypeEntity:
    """Сущность типа поставки (справочник)."""
    id: int | None = None
    delivery_type_id: str = ""


@dataclass
class TradeEntity:
    """Сущность сделки — основная запись учёта торгов."""
    id: int | None = None
    url: str = ""
    file_path: str | None = None
    product_id: int | None = None
    delivery_basis_id: int | None = None
    delivery_type_id: int | None = None
    volume: float | None = None
    total: float | None = None
    count: int | None = None
    date: datetime | None = None
    created_on: datetime | None = None
    updated_on: datetime | None = None
