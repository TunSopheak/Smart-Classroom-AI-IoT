from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("classroom_id", "student_id", name="uq_enrollment_classroom_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    classroom = relationship("Classroom", back_populates="enrollments")
    student = relationship("Student", back_populates="enrollments")
