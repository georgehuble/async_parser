from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import DeliveryTypeEntity
from src.domain.interfaces.repositories.abstracts import DeliveryTypeRepositoryAbstract
from src.domain.value_objects import DeliveryTypeId

from ..models import DeliveryType


class DeliveryTypeRepository(DeliveryTypeRepositoryAbstract):
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
            delivery_type_id=DeliveryTypeId(instance.delivery_type_id) if instance.delivery_type_id else None,
        )

    async def get_by_id(self, type_id: str) -> DeliveryTypeEntity | None:
        query = select(DeliveryType).where(DeliveryType.delivery_type_id == type_id)
        result = await self._db_session.execute(query)
        instance = result.scalar_one_or_none()
        if instance is None:
            return None
        return DeliveryTypeEntity(
            delivery_type_id=DeliveryTypeId(instance.delivery_type_id) if instance.delivery_type_id else None,
        )
