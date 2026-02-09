from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine.url import make_url
import ssl

from core.config import env

url = make_url(env.database_url)
connect_args = {}

if url.query.get("ssl") == "true":
    connect_args["ssl"] = ssl.create_default_context()

engine = create_async_engine(
    env.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args,
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