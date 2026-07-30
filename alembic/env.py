from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from src.infra.database.config import settings
from src.infra.database.models import Base

config = context.config
target_metadata = Base.metadata

# Получаем асинхронный URL из нашего config.py (который уже прочитал .env)
db_url = settings.database_url

# Alembic требует синхронный драйвер (psycopg2) для генерации миграций (--autogenerate).
# Автоматически меняем asyncpg на psycopg2.
# Если у вас в .env уже написан psycopg2, эта строка ничего не сломает.
sync_db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

# Устанавливаем URL для Alembic
config.set_main_option("sqlalchemy.url", sync_db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode."""
    # Для реального применения миграций (upgrade head) возвращаем асинхронный URL
    config.set_main_option("sqlalchemy.url", db_url)

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    import asyncio

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
