import logging
from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import TradeEntity
from src.domain.interfaces.repositories.abstracts import TradeRepositoryAbstract
from src.domain.value_objects import Money, Volume

from ..models import Trade

logger = logging.getLogger(__name__)


class TradeRepository(TradeRepositoryAbstract):
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

    async def url_exists_by_date(self, dt: date, exchange_id: int) -> bool:
        """Проверяет, существует ли запись с указанной датой по бирже."""
        query = select(Trade.trade_id).where(Trade.date == dt, Trade.exchange_id == exchange_id)
        query = query.limit(1)
        result = await self._db_session.execute(query)
        return result.scalar_one_or_none() is not None

    async def add_url(self, url: str, dt: date | None = None, exchange_id: int = 0) -> TradeEntity:
        """Добавляет url с датой (для save_urls)."""
        instance = Trade(url=url, date=dt, exchange_id=exchange_id)
        self._db_session.add(instance)
        await self._db_session.flush()
        return TradeEntity(
            trade_id=instance.trade_id,
            exchange_id=instance.exchange_id,
            url=instance.url,
            date=instance.date,
        )

    async def add(
        self,
        url: str,
        dt: date | None = None,
        exchange_id: int = 0,
        exchange_trade_id: str | None = None,
        product_id: int | None = None,
        delivery_basis_id: str | None = None,
        delivery_type_id: str | None = None,
        volume: float | None = None,
        total: float | None = None,
        count: int | None = None,
    ) -> TradeEntity:
        """Добавляет запись о сделке с полными данными."""
        instance = Trade(
            url=url,
            date=dt,
            exchange_id=exchange_id,
            exchange_trade_id=exchange_trade_id,
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
            trade_id=instance.trade_id,
            exchange_id=instance.exchange_id,
            exchange_trade_id=instance.exchange_trade_id,
            url=instance.url,
            file_path=instance.file_path,
            product_id=instance.product_id,
            delivery_basis_id=instance.delivery_basis_id,
            delivery_type_id=instance.delivery_type_id,
            volume=Volume(value=instance.volume) if instance.volume is not None else None,
            total=Money(amount=instance.total) if instance.total is not None else None,
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
                trade_id=instance.trade_id,
                exchange_id=instance.exchange_id,
                exchange_trade_id=instance.exchange_trade_id,
                url=instance.url,
                file_path=instance.file_path,
                product_id=instance.product_id,
                delivery_basis_id=instance.delivery_basis_id,
                delivery_type_id=instance.delivery_type_id,
                volume=Volume(value=instance.volume) if instance.volume is not None else None,
                total=Money(amount=instance.total) if instance.total is not None else None,
                count=instance.count,
                date=instance.date,
                created_on=instance.created_on,
                updated_on=instance.updated_on,
            )
            for instance in instances
        ]

    async def update_file_path(self, trade_id: int, file_path: str) -> None:
        """Обновляет путь к файлу по ID сделки."""
        stmt = update(Trade).where(Trade.trade_id == trade_id).values(file_path=file_path)
        await self._db_session.execute(stmt)

    async def commit(self) -> None:
        """Коммитит транзакцию."""
        await self._db_session.commit()
