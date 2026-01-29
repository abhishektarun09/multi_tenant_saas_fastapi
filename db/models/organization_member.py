import enum

from sqlalchemy import Column, Integer, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text
from ..base import Base

class OrgRole(enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    
    id = Column(Integer, primary_key = True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Enum(OrgRole, name="org_role"), nullable=False, server_default=text("'member'"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'), onupdate=text("now()"))
    
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_user_org"),)
    
    users = relationship("User", back_populates="organizations")
    
    organization = relationship("Organization", back_populates="members")