import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings
from .models import Base

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url, echo=False, pool_pre_ping=True, pool_size=10, connect_args={"ssl": False}
)


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Возвращает асинхронную сессию для работы с БД.
    Используется как контекстный менеджер:

    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def clear_all_tables(session: AsyncSession) -> None:
    """Полностью очищает все таблицы БД, сохраняя их схему.

    Нужна для повторного запуска парсинга с нуля: удаляет все записи
    из всех таблиц, сбрасывает автоинкрементные счётчики (RESTART IDENTITY)
    и каскадно обходит внешние ключи (CASCADE).
    Таблица ``alembic_version`` не входит в ``Base.metadata`` и не затрагивается.

    Args:
        session: Асинхронная сессия SQLAlchemy.
    """
    # Порядок таблиц — обратный зависимостям по внешним ключам (сначала дочерние)
    table_names = ", ".join(table.name for table in reversed(Base.metadata.sorted_tables))
    stmt = text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
    await session.execute(stmt)
    logger.info("Все таблицы очищены: %s", table_names)
