"""Объекты-значения (Value Objects) предметной области.

ValueObject — неизменяемый объект, идентичность которого определяется
значениями его полей, а не уникальным идентификатором (как у Entity).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Exchange:
    """Наименование биржи, откуда получены данные (например 'SPIMEX', 'MOEX')."""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ExchangeProductId:
    """Код нефтепродукта на бирже (например 'A100NAS33G0')."""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class OilId:
    """Код нефти (например 'A100')."""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DeliveryBasisId:
    """Код базиса поставки (например 'NAS')."""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DeliveryTypeId:
    """Код типа поставки (односимвольный, например 'G')."""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Volume:
    """Объём продукции с единицей измерения (тонны, штуки и т.д.)."""
    value: float
    unit: str = "т"  # тонны — единица по умолчанию для нефтепродуктов

    def __float__(self) -> float:
        return self.value


@dataclass(frozen=True)
class Money:
    """Денежная сумма (рубли, если не указано иное)."""
    amount: float
    currency: str = "RUB"

    def __float__(self) -> float:
        return self.amount
