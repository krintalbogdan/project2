from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, REAL
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from db.database import Base

class gpsJob(Base):
    __tablename__ = 'gpsJob'
    id:int = Column(Integer, unique=True, primary_key=True)
    status:str = Column(String(10), unique=False)
    from_coord = Column('from', REAL, unique=False, nullable=False)
    to_coord = Column(REAL, unique=False, nullable=False)
    algorithm = Column(String(10), unique=False)