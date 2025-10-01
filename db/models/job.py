from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Integer, Float
from sqlalchemy.sql import func
from db.base import Base

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String(36), primary_key=True)          # uuid4
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    audio_path = Column(Text, nullable=False)
    transcript_path = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, index=True)  # PENDING/UPLOADING/RUNNING/CANCELLING/SUCCEEDED/FAILED
    error_message = Column(Text, nullable=True)
    logs_path = Column(Text, nullable=True)
    file_sha256 = Column(String(64), nullable=True)
    transcription_mode = Column(String(16), nullable=False, default="on-demand")
    diarization = Column(Boolean, nullable=False, default=False)
    diagnostics = Column(Boolean, nullable=False, default=False)
    # Persisted metrics
    audio_bytes = Column(Integer, nullable=True)
    audio_mime = Column(String(128), nullable=True)
    audio_ext = Column(String(16), nullable=True)
    audio_mtime = Column(DateTime(timezone=True), nullable=True)
    audio_bitrate_kbps = Column(Integer, nullable=True)
    audio_channels = Column(Integer, nullable=True)
    audio_duration_sec = Column(Integer, nullable=True)
    sample_rate_hz = Column(Integer, nullable=True)
    transcript_words = Column(Integer, nullable=True)
    transcript_bytes = Column(Integer, nullable=True)
    upload_progress = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
