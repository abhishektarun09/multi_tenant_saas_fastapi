import enum
from sqlalchemy import UUID, Column, ForeignKey, Integer, String, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql.expression import text

from database.db.base import Base


class Provider(enum.Enum):
    password = "password"
    google = "google"


class AuthIdentity(Base):
    __tablename__ = "auth_identities"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(Enum(Provider, name="provider"), nullable=False)
    provider_user_id = Column(String, nullable=True)
    password_hash = Column(String(255), nullable=True)

    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at_time = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()"),
        server_onupdate=text("now()"),
    )

    user = relationship("Users", back_populates="identities")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_providerid"),
    )
