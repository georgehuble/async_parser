from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import DeliveryBasisEntity
from src.domain.interfaces.repositories.abstracts import DeliveryBasisRepositoryAbstract
from src.domain.value_objects import DeliveryBasisId

from ..models import DeliveryBasis


class DeliveryBasisRepository(DeliveryBasisRepositoryAbstract):
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
            delivery_basis_id=DeliveryBasisId(instance.delivery_basis_id) if instance.delivery_basis_id else None,
            delivery_basis_name=instance.delivery_basis_name,
        )

    async def get_by_id(self, basis_id: str) -> DeliveryBasisEntity | None:
        query = select(DeliveryBasis).where(DeliveryBasis.delivery_basis_id == basis_id)
        result = await self._db_session.execute(query)
        instance = result.scalar_one_or_none()
        if instance is None:
            return None
        return DeliveryBasisEntity(
            delivery_basis_id=DeliveryBasisId(instance.delivery_basis_id) if instance.delivery_basis_id else None,
            delivery_basis_name=instance.delivery_basis_name,
        )
