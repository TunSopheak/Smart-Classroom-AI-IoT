from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    teacher = relationship("Teacher", back_populates="subjects")
    sessions = relationship("ClassSession", back_populates="subject")
