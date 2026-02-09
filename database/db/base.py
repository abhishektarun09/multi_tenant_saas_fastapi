from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import ssl

from core.config import env

ssl_context = ssl.create_default_context()

if env.dev:
    engine = create_async_engine(
        env.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
    )
else:
    engine = create_async_engine(
        env.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"ssl": ssl_context},
    )

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()

import database.models

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session