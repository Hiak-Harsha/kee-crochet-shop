from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Adjust connection arguments if we are using SQLite vs PostgreSQL
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Create the async engine
engine = create_async_engine(
    db_url,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create session factory
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency for acquiring database sessions."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
