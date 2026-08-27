from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Exchange(Base):
    """Справочник биржевых источников (SPIMEX, MOEX и т.д.)."""

    __tablename__ = "exchanges"

    exchange_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    oil_products: Mapped[list["OilProduct"]] = relationship(back_populates="exchange")
    trades: Mapped[list["Trade"]] = relationship(back_populates="exchange")

    def __repr__(self) -> str:
        return f"<Exchange(exchange_id={self.exchange_id}, name={self.name!r})>"


class OilProduct(Base):
    """Справочник нефтепродуктов."""

    __tablename__ = "oil_products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exchange_id: Mapped[int] = mapped_column(
        ForeignKey("exchanges.exchange_id"), nullable=False, index=True
    )
    exchange_product_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exchange_product_name: Mapped[str] = mapped_column(String(255), nullable=True)
    oil_id: Mapped[str] = mapped_column(String(4), nullable=True)

    exchange: Mapped[Exchange] = relationship(back_populates="oil_products")
    trades: Mapped[list["Trade"]] = relationship(back_populates="product")

    __table_args__ = (
        UniqueConstraint("exchange_id", "exchange_product_id", name="uix_oil_product_exchange"),
    )


class DeliveryBasis(Base):
    """Справочник базисов поставки."""

    __tablename__ = "delivery_bases"

    delivery_basis_id: Mapped[str] = mapped_column(String(3), primary_key=True)
    delivery_basis_name: Mapped[str] = mapped_column(String(100), nullable=True)

    trades: Mapped[list["Trade"]] = relationship(back_populates="delivery_basis")


class DeliveryType(Base):
    """Справочник типов поставки."""

    __tablename__ = "delivery_types"

    delivery_type_id: Mapped[str] = mapped_column(String(1), primary_key=True)

    trades: Mapped[list["Trade"]] = relationship(back_populates="delivery_type")


class Trade(Base):
    """Сделка — основная таблица учёта торгов."""

    __tablename__ = "trades"

    trade_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exchange_id: Mapped[int] = mapped_column(
        ForeignKey("exchanges.exchange_id"), nullable=False, index=True
    )
    exchange_trade_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    product_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("oil_products.product_id"), nullable=True, index=True
    )
    delivery_basis_id: Mapped[str | None] = mapped_column(
        String(3), ForeignKey("delivery_bases.delivery_basis_id"), nullable=True, index=True
    )
    delivery_type_id: Mapped[str | None] = mapped_column(
        String(1), ForeignKey("delivery_types.delivery_type_id"), nullable=True, index=True
    )

    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    total: Mapped[float | None] = mapped_column(Float, nullable=True)
    count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    exchange: Mapped[Exchange] = relationship(back_populates="trades")
    product: Mapped[OilProduct | None] = relationship(back_populates="trades")
    delivery_basis: Mapped[DeliveryBasis | None] = relationship(back_populates="trades")
    delivery_type: Mapped[DeliveryType | None] = relationship(back_populates="trades")

    __table_args__ = (
        UniqueConstraint("exchange_id", "exchange_trade_id", name="uix_exchange_trade"),
        # Бизнес-ключ бюллетеней: (exchange_id, url) уникален только для строк без exchange_trade_id
        Index(
            "uix_exchange_url",
            "exchange_id",
            "url",
            unique=True,
            postgresql_where=text("exchange_trade_id IS NULL"),
        ),
    )
