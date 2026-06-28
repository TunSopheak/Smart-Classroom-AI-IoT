from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AttendanceEvent(Base):
    __tablename__ = "attendance_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id"), nullable=False)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    result: Mapped[str] = mapped_column(String(30), nullable=False, default="success")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    session = relationship("ClassSession", back_populates="attendance_events")
    student = relationship("Student", back_populates="attendance_events")
