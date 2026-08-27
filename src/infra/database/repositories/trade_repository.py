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
    """Репозиторий сделок (таблица trades).

    Универсален: принадлежность к бирже задаёт exchange_id.
    Записи идентифицируются по бизнес-ключам, а не по автоинкрементному trade_id:
    - бюллетени — (exchange_id, url);
    - сделки — (exchange_id, exchange_trade_id).
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def get_max_date(self) -> date | None:
        """Максимальная дата в таблице trades."""
        query = select(func.max(Trade.date))
        result = await self._db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_links(self) -> list[tuple[date, str, int]]:
        """Возвращает (дата, url, exchange_id) для скачивания файлов."""
        query = select(Trade.date, Trade.url, Trade.exchange_id).where(Trade.date.isnot(None))
        try:
            result = await self._db_session.execute(query)
            rows = result.all()
        except Exception:
            logger.exception("Ошибка выполнения запроса")
            raise
        logger.info("Получено %d ссылок из БД", len(rows))
        return [(row.date, row.url, row.exchange_id) for row in rows]

    async def url_exists(self, url: str, exchange_id: int) -> bool:
        """Проверяет существование записи по бизнес-ключу (exchange_id, url)."""
        query = select(Trade.trade_id).where(Trade.url == url, Trade.exchange_id == exchange_id)
        query = query.limit(1)
        result = await self._db_session.execute(query)
        return result.scalar_one_or_none() is not None

    async def add_url(self, url: str, dt: date | None = None, exchange_id: int = 0) -> TradeEntity:
        """Upsert бюллетеня по бизнес-ключу (exchange_id, url)."""
        instance = await self._get_by_url(url, exchange_id)
        if instance is None:
            instance = Trade(url=url, date=dt, exchange_id=exchange_id)
            self._db_session.add(instance)
        elif dt is not None:
            instance.date = dt
        await self._db_session.flush()
        return self._to_entity(instance)

    async def add_trades(self, trades: list[TradeEntity]) -> None:
        """Массово добавляет сделки без проверки существования по бизнес-ключу.

        Вызывающий код обязан отфильтровать уже существующие сделки
        (например, через ``get_existing_trade_ids``). Поля TradeEntity
        (product_id, url) должны быть уже разрешены.
        """
        if not trades:
            return

        instances = [
            Trade(
                url=trade.url,
                date=trade.date,
                exchange_id=trade.exchange_id or 0,
                exchange_trade_id=trade.exchange_trade_id,
                product_id=trade.product_id,
                delivery_basis_id=trade.delivery_basis_id,
                delivery_type_id=trade.delivery_type_id,
                volume=float(trade.volume) if trade.volume is not None else None,
                total=float(trade.total) if trade.total is not None else None,
                count=trade.count,
                file_path=trade.file_path,
            )
            for trade in trades
        ]
        self._db_session.add_all(instances)
        await self._db_session.flush()

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
        file_path: str | None = None,
    ) -> TradeEntity:
        """Upsert сделки по бизнес-ключу (exchange_id, exchange_trade_id)."""
        instance = (
            await self._get_by_exchange_trade_id(exchange_trade_id, exchange_id)
            if exchange_trade_id is not None
            else None
        )

        if instance is None:
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
                file_path=file_path,
            )
            self._db_session.add(instance)
        else:
            instance.url = url
            instance.date = dt
            instance.product_id = product_id
            instance.delivery_basis_id = delivery_basis_id
            instance.delivery_type_id = delivery_type_id
            instance.volume = volume
            instance.total = total
            instance.count = count
            instance.file_path = file_path

        await self._db_session.flush()
        return self._to_entity(instance)

    async def get_bulletin_url_by_date(self, dt: date, exchange_id: int) -> str | None:
        """Возвращает URL бюллетеня для даты (строка без exchange_trade_id).

        Args:
            dt: Дата торгов.
            exchange_id: Идентификатор биржевого источника.

        Returns:
            URL бюллетеня или None, если запись не найдена.
        """
        query = (
            select(Trade.url)
            .where(
                Trade.date == dt,
                Trade.exchange_id == exchange_id,
                Trade.exchange_trade_id.is_(None),
            )
            .limit(1)
        )
        result = await self._db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_existing_trade_ids(self, exchange_id: int, trade_ids: list[str]) -> set[str]:
        """Возвращает exchange_trade_id уже существующих сделок (для пропуска дубликатов).

        Args:
            exchange_id: Идентификатор биржевого источника.
            trade_ids: Список business-ключей сделок для проверки.

        Returns:
            Множество exchange_trade_id, найденных в БД.
        """
        if not trade_ids:
            return set()
        query = select(Trade.exchange_trade_id).where(
            Trade.exchange_id == exchange_id,
            Trade.exchange_trade_id.in_(trade_ids),
        )
        result = await self._db_session.execute(query)
        return {trade_id for trade_id in result.scalars().all() if trade_id is not None}

    async def update_file_path_by_url(self, url: str, exchange_id: int, file_path: str) -> None:
        """Обновляет путь к файлу по бизнес-ключу (exchange_id, url)."""
        stmt = update(Trade).where(Trade.url == url, Trade.exchange_id == exchange_id).values(file_path=file_path)
        await self._db_session.execute(stmt)

    async def get_by_date(self, dt: date) -> list[TradeEntity]:
        """Возвращает сделки по дате."""
        query = select(Trade).where(Trade.date == dt)
        result = await self._db_session.execute(query)
        instances = result.scalars().all()
        return [self._to_entity(instance) for instance in instances]

    async def commit(self) -> None:
        """Коммитит транзакцию."""
        await self._db_session.commit()

    async def _get_by_url(self, url: str, exchange_id: int) -> Trade | None:
        """Ищет запись бюллетеня по бизнес-ключу (exchange_id, url)."""
        query = select(Trade).where(Trade.url == url, Trade.exchange_id == exchange_id).limit(1)
        result = await self._db_session.execute(query)
        return result.scalar_one_or_none()

    async def _get_by_exchange_trade_id(self, exchange_trade_id: str, exchange_id: int) -> Trade | None:
        """Ищет сделку по бизнес-ключу (exchange_id, exchange_trade_id)."""
        query = select(Trade).where(
            Trade.exchange_trade_id == exchange_trade_id,
            Trade.exchange_id == exchange_id,
        ).limit(1)
        result = await self._db_session.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    def _to_entity(instance: Trade) -> TradeEntity:
        """Преобразует модель БД в доменную сущность."""
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
            created_on=instance.created_on,
            updated_on=instance.updated_on,
        )
