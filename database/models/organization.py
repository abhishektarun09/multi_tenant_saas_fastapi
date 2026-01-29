from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text

from database.db.base import Base

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key = True, nullable = False)
    name = Column(String, nullable= False)
    slug = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'), onupdate=text("now()"))
    
    members = relationship("OrganizationMember", back_populates="organization")

    projects = relationship("Project", back_populates="organization")