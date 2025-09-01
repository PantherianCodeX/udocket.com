from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from db.base import Base

class Case(Base):
    __tablename__ = "cases"
    id = Column(String(36), primary_key=True)  # uuid4
    title = Column(String(200), nullable=False)
    reference = Column(String(100), nullable=True, index=True)
    party_1 = Column(String(120), nullable=True)
    party_2 = Column(String(120), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())