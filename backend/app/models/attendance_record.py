from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("session_id", "student_id", name="uq_attendance_record_session_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    first_seen_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(5), default="A", nullable=False)
    method: Mapped[str] = mapped_column(String(20), default="SYSTEM", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    overridden_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    session = relationship("ClassSession", back_populates="attendance_records")
    student = relationship("Student", back_populates="attendance_records")
