import logging
from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import (
    DeliveryBasisEntity,
    DeliveryTypeEntity,
    OilProductEntity,
    TradeEntity,
)

from .models import DeliveryBasis, DeliveryType, OilProduct, Trade

logger = logging.getLogger(__name__)


class TradeRepository:
    """Репозиторий сделок (таблица trades)."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def get_max_date(self) -> date | None:
        """Возвращает максимальную дату из таблицы trades."""
        query = select(func.max(Trade.date))
        result = await self._db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_links(self) -> list[tuple[date, str]]:
        """Возвращает (дата, url) для скачивания файлов."""
        query = select(Trade.date, Trade.url).where(Trade.date.isnot(None))
        try:
            result = await self._db_session.execute(query)
            rows = result.all()
        except Exception:
            logger.exception("Ошибка выполнения запроса")
            raise
        logger.info("Получено %d ссылок из БД", len(rows))
        return [(row.date, row.url) for row in rows]

    async def url_exists_by_date(self, dt: date) -> bool:
        """Проверяет, существует ли запись с указанной датой."""
        query = select(Trade.id).where(Trade.date == dt).limit(1)
        result = await self._db_session.execute(query)
        return result.scalar_one_or_none() is not None

    async def add_url(self, url: str, dt: date | None = None) -> TradeEntity:
        """Добавляет url с датой (для save_urls)."""
        instance = Trade(url=url, date=dt)
        self._db_session.add(instance)
        await self._db_session.flush()
        return TradeEntity(
            id=instance.id,
            url=instance.url,
            date=instance.date,
        )

    async def add(
        self,
        url: str,
        dt: date | None = None,
        product_id: int | None = None,
        delivery_basis_id: int | None = None,
        delivery_type_id: int | None = None,
        volume: float | None = None,
        total: float | None = None,
        count: int | None = None,
    ) -> TradeEntity:
        """Добавляет запись о сделке с полными данными."""
        instance = Trade(
            url=url,
            date=dt,
            product_id=product_id,
            delivery_basis_id=delivery_basis_id,
            delivery_type_id=delivery_type_id,
            volume=volume,
            total=total,
            count=count,
        )
        self._db_session.add(instance)
        await self._db_session.flush()
        return TradeEntity(
            id=instance.id,
            url=instance.url,
            file_path=instance.file_path,
            product_id=instance.product_id,
            delivery_basis_id=instance.delivery_basis_id,
            delivery_type_id=instance.delivery_type_id,
            volume=instance.volume,
            total=instance.total,
            count=instance.count,
            date=instance.date,
        )

    async def update_file_path_by_date(self, dt: date, file_path: str) -> None:
        """Обновляет путь к файлу по дате."""
        stmt = update(Trade).where(Trade.date == dt).values(file_path=file_path)
        await self._db_session.execute(stmt)

    async def get_by_date(self, dt: date) -> list[TradeEntity]:
        """Возвращает сделки по дате."""
        query = select(Trade).where(Trade.date == dt)
        result = await self._db_session.execute(query)
        instances = result.scalars().all()
        return [
            TradeEntity(
                id=instance.id,
                url=instance.url,
                file_path=instance.file_path,
                product_id=instance.product_id,
                delivery_basis_id=instance.delivery_basis_id,
                delivery_type_id=instance.delivery_type_id,
                volume=instance.volume,
                total=instance.total,
                count=instance.count,
                date=instance.date,
                created_on=instance.created_on,
                updated_on=instance.updated_on,
            )
            for instance in instances
        ]

    async def update_file_path(self, trade_id: int, file_path: str) -> None:
        """Обновляет путь к файлу по ID сделки."""
        stmt = update(Trade).where(Trade.id == trade_id).values(file_path=file_path)
        await self._db_session.execute(stmt)

    async def commit(self) -> None:
        """Коммитит транзакцию."""
        await self._db_session.commit()


class OilProductRepository:
    """Репозиторий справочника нефтепродуктов."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def get_or_create(
        self, exchange_product_id: str, name: str | None, oil_id: str | None
    ) -> OilProductEntity:
        """Ищет запись по exchange_product_id, если нет — создаёт."""
        query = select(OilProduct).where(OilProduct.exchange_product_id == exchange_product_id)
        result = await self._db_session.execute(query)
        instance = result.scalar_one_or_none()

        if instance is None:
            instance = OilProduct(
                exchange_product_id=exchange_product_id,
                exchange_product_name=name,
                oil_id=oil_id,
            )
            self._db_session.add(instance)
            await self._db_session.flush()

        return OilProductEntity(
            id=instance.id,
            exchange_product_id=instance.exchange_product_id,
            exchange_product_name=instance.exchange_product_name,
            oil_id=instance.oil_id,
        )

    async def get_by_id(self, product_id: int) -> OilProductEntity | None:
        query = select(OilProduct).where(OilProduct.id == product_id)
        result = await self._db_session.execute(query)
        instance = result.scalar_one_or_none()
        if instance is None:
            return None
        return OilProductEntity(
            id=instance.id,
            exchange_product_id=instance.exchange_product_id,
            exchange_product_name=instance.exchange_product_name,
            oil_id=instance.oil_id,
        )


class DeliveryBasisRepository:
    """Репозиторий справочника базисов поставки."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def get_or_create(self, delivery_basis_id: str, name: str | None) -> DeliveryBasisEntity:
        query = select(DeliveryBasis).where(DeliveryBasis.delivery_basis_id == delivery_basis_id)
        result = await self._db_session.execute(query)
        instance = result.scalar_one_or_none()

        if instance is None:
            instance = DeliveryBasis(
                delivery_basis_id=delivery_basis_id,
                delivery_basis_name=name,
            )
            self._db_session.add(instance)
            await self._db_session.flush()

        return DeliveryBasisEntity(
            id=instance.id,
            delivery_basis_id=instance.delivery_basis_id,
            delivery_basis_name=instance.delivery_basis_name,
        )

    async def get_by_id(self, basis_id: int) -> DeliveryBasisEntity | None:
        query = select(DeliveryBasis).where(DeliveryBasis.id == basis_id)
        result = await self._db_session.execute(query)
        instance = result.scalar_one_or_none()
        if instance is None:
            return None
        return DeliveryBasisEntity(
            id=instance.id,
            delivery_basis_id=instance.delivery_basis_id,
            delivery_basis_name=instance.delivery_basis_name,
        )


class DeliveryTypeRepository:
    """Репозиторий справочника типов поставки."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def get_or_create(self, delivery_type_id: str) -> DeliveryTypeEntity:
        query = select(DeliveryType).where(DeliveryType.delivery_type_id == delivery_type_id)
        result = await self._db_session.execute(query)
        instance = result.scalar_one_or_none()

        if instance is None:
            instance = DeliveryType(delivery_type_id=delivery_type_id)
            self._db_session.add(instance)
            await self._db_session.flush()

        return DeliveryTypeEntity(
            id=instance.id,
            delivery_type_id=instance.delivery_type_id,
        )

    async def get_by_id(self, type_id: int) -> DeliveryTypeEntity | None:
        query = select(DeliveryType).where(DeliveryType.id == type_id)
        result = await self._db_session.execute(query)
        instance = result.scalar_one_or_none()
        if instance is None:
            return None
        return DeliveryTypeEntity(
            id=instance.id,
            delivery_type_id=instance.delivery_type_id,
        )
