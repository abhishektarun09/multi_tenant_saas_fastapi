import enum
from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text

from database.db.base import Base

class UserStatus(enum.Enum):
    active = "active"
    inactive = "inactive"

class Users(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key = True, nullable = False)
    name = Column(String, nullable= False)
    email = Column(String, nullable= False, unique=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(Enum(UserStatus, name="user_status"), nullable=False, server_default=text("'active'"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    updated_at_time = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'), server_onupdate=text("now()"))
    
    organizations = relationship("OrganizationMember", back_populates="users")
    
    projects = relationship("Project", back_populates="creator")