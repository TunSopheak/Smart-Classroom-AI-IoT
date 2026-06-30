from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ClassSession(Base):
    __tablename__ = "class_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    class_group_id: Mapped[int | None] = mapped_column(ForeignKey("class_groups.id"), nullable=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    weekly_schedule_id: Mapped[int | None] = mapped_column(ForeignKey("weekly_schedules.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    late_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    archived = Column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    classroom = relationship("Classroom", back_populates="sessions")
    subject = relationship("Subject", back_populates="sessions")
    class_group = relationship("ClassGroup", back_populates="sessions")
    course = relationship("Course", back_populates="sessions")
    weekly_schedule = relationship("WeeklySchedule", back_populates="sessions")
    attendance_records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")
    attendance_events = relationship("AttendanceEvent", back_populates="session", cascade="all, delete-orphan")
