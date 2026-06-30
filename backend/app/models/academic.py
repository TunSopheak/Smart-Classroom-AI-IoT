from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ClassGroup(Base):
    __tablename__ = "class_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    academic_year: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    enrollments = relationship("StudentEnrollment", back_populates="class_group", cascade="all, delete-orphan")
    schedules = relationship("WeeklySchedule", back_populates="class_group", cascade="all, delete-orphan")
    sessions = relationship("ClassSession", back_populates="class_group")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    schedules = relationship("WeeklySchedule", back_populates="course", cascade="all, delete-orphan")
    sessions = relationship("ClassSession", back_populates="course")


class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"
    __table_args__ = (UniqueConstraint("student_id", "class_group_id", name="uq_student_class_group"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    class_group_id: Mapped[int] = mapped_column(ForeignKey("class_groups.id"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="class_group_enrollments")
    class_group = relationship("ClassGroup", back_populates="enrollments")


class WeeklySchedule(Base):
    __tablename__ = "weekly_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    class_group_id: Mapped[int] = mapped_column(ForeignKey("class_groups.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    late_after_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    class_group = relationship("ClassGroup", back_populates="schedules")
    course = relationship("Course", back_populates="schedules")
    sessions = relationship("ClassSession", back_populates="weekly_schedule")
