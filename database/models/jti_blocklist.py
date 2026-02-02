from sqlalchemy import Column, String, Integer
from database.db.base import Base

class JtiBlocklist(Base):
    __tablename__ = "jti_blocklist"
    
    id = Column(Integer, primary_key = True)
    jti = Column(String, nullable=False)