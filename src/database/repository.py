import logging
from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import ExchangeRecord

from .models import Spimex

logger = logging.getLogger(__name__)


class SpimexUploadRepository:
    """Репозиторий для загрузки (записи) ссылок в БД."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def url_exists_by_date(self, date: date) -> bool:
        """Проверяет, существует ли запись с указанной датой."""
        query = select(Spimex.id).where(Spimex.date == date).limit(1)
        result = await self._db_session.execute(query)
        return result.scalar_one_or_none() is not None

    async def add_url(self, url: str, date: date | None = None) -> ExchangeRecord:
        record = Spimex(url=url, date=date)
        self._db_session.add(record)
        await self._db_session.flush()
        return ExchangeRecord(id=record.id, url=record.url)


class SpimexDownloadRepository:
    """Репозиторий для скачивания (чтения/обновления) файлов."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def get_max_date(self) -> date | None:
        """Возвращает максимальную дату из таблицы results."""
        query = select(func.max(Spimex.date))
        result = await self._db_session.execute(query)
        max_date = result.scalar_one_or_none()
        return max_date

    async def get_links(self) -> list[tuple[date, str]]:
        query = select(Spimex.date, Spimex.url).where(Spimex.date.isnot(None))
        try:
            result = await self._db_session.execute(query)
            rows = result.all()
        except Exception:
            logger.exception("Ошибка выполнения запроса")
            raise
        logger.info("Получено %d ссылок из БД", len(rows))
        return [(row.date, row.url) for row in rows]

    async def update_file_path_by_date(self, dt: date, file_path: str) -> None:
        stmt = update(Spimex).where(Spimex.date == dt).values(file_path=file_path)
        await self._db_session.execute(stmt)

    async def commit(self) -> None:
        await self._db_session.commit()
