import psycopg2

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from core.config import env

# Local PostgreSQL Database
SQL_ALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{env.database_username}:{env.database_password}@{env.database_hostname}:{env.database_port}/{env.database_name}"

# # Cloud PostgreSQL Database (Neon)
# SQL_ALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{env.database_username}:{env.database_password}@{env.database_hostname}:{env.database_port}/{env.database_name}?sslmode=require&channel_binding=require"

engine = create_engine(SQL_ALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

import database.models

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()