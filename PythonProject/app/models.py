from sqlalchemy import Column, Integer, String
from geoalchemy2 import Geometry
from app.database import Base
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    location = Column(Geometry("POINT", srid=4326))
    event_type = Column(String, nullable=True)

class Shelter(Base):
    __tablename__ = "shelters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    coordinates = Column(Geometry("POINT", srid=4326))
    capacity = Column(Integer)