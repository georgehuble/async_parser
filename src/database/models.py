from datetime import datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Spimex(Base):
    __tablename__ = "results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    file_path: Mapped[str] = mapped_column(String(500), nullable=True)

    exchange_product_id: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    exchange_product_name: Mapped[str] = mapped_column(String(255), nullable=True)

    oil_id: Mapped[str] = mapped_column(String(4), nullable=True)
    delivery_basis_id: Mapped[str] = mapped_column(String(3), nullable=True)
    delivery_basis_name: Mapped[str] = mapped_column(String(100), nullable=True)
    delivery_type_id: Mapped[str] = mapped_column(String(1), nullable=True)

    volume: Mapped[float] = mapped_column(Float, nullable=True)
    total: Mapped[float] = mapped_column(Float, nullable=True)
    count: Mapped[int] = mapped_column(Integer, nullable=True)

    date: Mapped[datetime] = mapped_column(Date, unique=True, nullable=True, index=True)

    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    updated_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("exchange_product_id", "delivery_basis_name", "date", name="uix_unique_product_basis_date"),
    )
