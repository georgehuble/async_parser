from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExchangeRecord:
    id: int | None = None
    url: str = ""
    file_path: str | None = None
    exchange_product_id: str | None = None
    exchange_product_name: str | None = None
    oil_id: str | None = None
    delivery_basis_id: str | None = None
    delivery_basis_name: str | None = None
    delivery_type_id: str | None = None
    volume: float | None = None
    total: float | None = None
    count: int | None = None
    date: datetime | None = None
    created_on: datetime | None = None
    updated_on: datetime | None = None
