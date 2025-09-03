from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from db.base import Base

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String(36), primary_key=True)          # uuid4
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    audio_path = Column(Text, nullable=False)
    transcript_path = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, index=True)  # PENDING/RUNNING/SUCCEEDED/FAILED
    error_message = Column(Text, nullable=True)
    logs_path = Column(Text, nullable=True)
    file_sha256 = Column(String(64), nullable=True)
    transcription_mode = Column(String(16), nullable=False, default="on-demand")
    diarization = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
