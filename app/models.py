from datetime import datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Parsered(Base):
    __tablename__ = "results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    exchange_product_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exchange_product_name: Mapped[str] = mapped_column(String(255), nullable=False)

    oil_id: Mapped[str] = mapped_column(String(4), nullable=False)
    delivery_basis_id: Mapped[str] = mapped_column(String(3), nullable=False)
    delivery_basis_name: Mapped[str] = mapped_column(String(100), nullable=False)
    delivery_type_id: Mapped[str] = mapped_column(String(1), nullable=False)

    volume: Mapped[float] = mapped_column(Float, nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)

    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)

    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "exchange_product_id",
            "delivery_basis_name",
            "date",
            name="uix_unique_product_basis_date"
        ),
    )
