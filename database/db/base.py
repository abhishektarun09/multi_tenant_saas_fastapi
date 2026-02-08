import psycopg2

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from core.config import env

engine = create_engine(env.database_url, pool_pre_ping=True, pool_recycle=300,)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

import database.models

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()