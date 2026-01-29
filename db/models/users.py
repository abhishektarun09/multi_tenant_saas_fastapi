from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from ..base import Base

class Users(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key = True, nullable = False)
    name = Column(String, nullable= False)
    email = Column(String, nullable= False, unique=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))