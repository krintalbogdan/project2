from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, REAL
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from db.database import Base

class gpsJob(Base):
    __tablename__ = 'gpsJob'
    id:int = Column(Integer, unique=True, primary_key=True)
    status:str = Column(String(10), unique=False)
    from_coord = Column(JSON, default=[])
    to_coord = Column(JSON, default=[])
    algorithm = Column(String(10), unique=False)
    path = Column(JSON, default=[])