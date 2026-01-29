from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from ..base import Base


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key = True)
    name = Column(String, nullable= False)    
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'), onupdate=text("now()"))

    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_org_project_name"),)
    
    organization = relationship("Organization", back_populates="projects")
    creator = relationship("User", back_populates="projects")