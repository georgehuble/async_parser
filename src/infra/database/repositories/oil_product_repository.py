from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import OilProductEntity
from src.domain.interfaces.repositories.abstracts import OilProductRepositoryAbstract
from src.domain.value_objects import ExchangeProductId, OilId

from ..models import OilProduct


class OilProductRepository(OilProductRepositoryAbstract):
    """Репозиторий справочника нефтепродуктов."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def get_or_create(
        self,
        exchange_product_id: str,
        name: str | None,
        oil_id: str | None,
        exchange_id: int,
    ) -> OilProductEntity:
        """Ищет запись по exchange_product_id + exchange_id, если нет — создаёт."""
        query = select(OilProduct).where(
            OilProduct.exchange_product_id == exchange_product_id,
            OilProduct.exchange_id == exchange_id,
        )
        result = await self._db_session.execute(query)
        instance = result.scalar_one_or_none()

        if instance is None:
            instance = OilProduct(
                exchange_product_id=exchange_product_id,
                exchange_product_name=name,
                oil_id=oil_id,
                exchange_id=exchange_id,
            )
            self._db_session.add(instance)
            await self._db_session.flush()

        return OilProductEntity(
            product_id=instance.product_id,
            exchange_id=instance.exchange_id,
            exchange_product_id=(
                ExchangeProductId(instance.exchange_product_id) if instance.exchange_product_id else None
            ),
            exchange_product_name=instance.exchange_product_name,
            oil_id=OilId(instance.oil_id) if instance.oil_id else None,
        )

    async def get_by_id(self, product_id: int) -> OilProductEntity | None:
        query = select(OilProduct).where(OilProduct.product_id == product_id)
        result = await self._db_session.execute(query)
        instance = result.scalar_one_or_none()
        if instance is None:
            return None
        return OilProductEntity(
            product_id=instance.product_id,
            exchange_id=instance.exchange_id,
            exchange_product_id=(
                ExchangeProductId(instance.exchange_product_id) if instance.exchange_product_id else None
            ),
            exchange_product_name=instance.exchange_product_name,
            oil_id=OilId(instance.oil_id) if instance.oil_id else None,
        )
