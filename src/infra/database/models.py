from datetime import datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class OilProduct(Base):
    """Справочник нефтепродуктов."""

    __tablename__ = "oil_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exchange: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    exchange_product_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exchange_product_name: Mapped[str] = mapped_column(String(255), nullable=True)
    oil_id: Mapped[str] = mapped_column(String(4), nullable=True)

    trades: Mapped[list["Trade"]] = relationship(back_populates="product")

    __table_args__ = (
        UniqueConstraint("exchange", "exchange_product_id", name="uix_oil_product_exchange"),
    )


class DeliveryBasis(Base):
    """Справочник базисов поставки."""

    __tablename__ = "delivery_bases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    delivery_basis_id: Mapped[str] = mapped_column(String(3), unique=True, nullable=False, index=True)
    delivery_basis_name: Mapped[str] = mapped_column(String(100), nullable=True)

    trades: Mapped[list["Trade"]] = relationship(back_populates="delivery_basis")


class DeliveryType(Base):
    """Справочник типов поставки."""

    __tablename__ = "delivery_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    delivery_type_id: Mapped[str] = mapped_column(String(1), unique=True, nullable=False, index=True)

    trades: Mapped[list["Trade"]] = relationship(back_populates="delivery_type")


class Trade(Base):
    """Сделка — основная таблица учёта торгов."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exchange: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    exchange_trade_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=True)

    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("oil_products.id"), nullable=True, index=True
    )
    delivery_basis_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("delivery_bases.id"), nullable=True, index=True
    )
    delivery_type_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("delivery_types.id"), nullable=True, index=True
    )

    volume: Mapped[float] = mapped_column(Float, nullable=True)
    total: Mapped[float] = mapped_column(Float, nullable=True)
    count: Mapped[int] = mapped_column(Integer, nullable=True)

    date: Mapped[datetime] = mapped_column(Date, nullable=True, index=True)

    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    product: Mapped[OilProduct | None] = relationship(back_populates="trades")
    delivery_basis: Mapped[DeliveryBasis | None] = relationship(back_populates="trades")
    delivery_type: Mapped[DeliveryType | None] = relationship(back_populates="trades")

    __table_args__ = (
        UniqueConstraint("exchange", "exchange_trade_id", name="uix_exchange_trade"),
    )
