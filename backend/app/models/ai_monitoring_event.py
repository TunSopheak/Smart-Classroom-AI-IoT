from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class AIMonitoringEvent(Base):
    __tablename__ = "ai_monitoring_events"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(Integer, ForeignKey("class_sessions.id"), nullable=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)

    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="info", index=True)
    confidence = Column(Float, nullable=True)

    source = Column(String(80), nullable=False, default="manual_simulation")
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    session = relationship("ClassSession")
    student = relationship("Student")
