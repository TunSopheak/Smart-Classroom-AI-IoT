from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stu_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    qr_code: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    qr_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    face_dataset_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="student")
    attendance_events = relationship("AttendanceEvent", back_populates="student")
