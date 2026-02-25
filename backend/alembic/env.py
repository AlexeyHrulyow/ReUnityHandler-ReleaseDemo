import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context

# Импортируем Base из вашего проекта
from reunity_app.db.base import Base
from reunity_app.core.config import settings

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# target_metadata для autogenerate
target_metadata = Base.metadata

# Функция для получения синхронного URL (без +asyncpg)
def get_sync_url():
    return settings.DATABASE_URL.replace("+asyncpg", "")

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Создаём синхронный движок
    sync_engine = create_engine(get_sync_url(), poolclass=pool.NullPool)

    with sync_engine.connect() as connection:
        do_run_migrations(connection)

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())