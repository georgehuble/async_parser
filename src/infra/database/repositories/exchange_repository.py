from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import ExchangeEntity
from src.domain.interfaces.repositories.abstracts import ExchangeRepositoryAbstract

from ..models import Exchange


class ExchangeRepository(ExchangeRepositoryAbstract):
    """Репозиторий биржевых источников (таблица exchanges)."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def get_id_by_name(self, name: str) -> int | None:
        """Возвращает exchange_id по названию биржи."""
        query = select(Exchange.exchange_id).where(Exchange.name == name)
        result = await self._db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create_by_name(self, name: str) -> ExchangeEntity:
        """Ищет биржу по названию, если нет — создаёт."""
        query = select(Exchange).where(Exchange.name == name)
        result = await self._db_session.execute(query)
        instance = result.scalar_one_or_none()

        if instance is None:
            instance = Exchange(name=name)
            self._db_session.add(instance)
            await self._db_session.flush()

        return ExchangeEntity(
            exchange_id=instance.exchange_id,
            name=instance.name,
        )
