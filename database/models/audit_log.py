import enum
from uuid import uuid4

from sqlalchemy import JSON, UUID, Column, Integer, ForeignKey, Enum, UniqueConstraint, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text

from database.db.base import Base

class AuditLog(Base):
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    action = Column(String, nullable=False) #user.created, login.success, login.failed etc.
    resource_type = Column(String, nullable=False) #user, organization, invoice, project
    resource_id = Column(String, nullable=False)
    status = Column(String, default="success") #success, failed, denied
    
    meta_data = Column(JSON)
    
    ip_address = Column(String)
    user_agent = Column(String)
    endpoint = Column(String)