import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://realestate:password@db:5432/realestate")
# SQLAlchemy async requires +asyncpg driver prefix
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create all tables on startup with retry logic."""
    import models  # noqa: F401 — ensures models are registered on Base
    for attempt in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("[DB] Tables created successfully.")
            return
        except Exception as e:
            print(f"[DB] Connection attempt {attempt + 1}/10 failed: {e}")
            await asyncio.sleep(2)
    raise RuntimeError("[DB] Could not connect to PostgreSQL after 10 attempts.")
