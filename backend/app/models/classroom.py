from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Classroom(Base):
    __tablename__ = "classrooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    section: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shift: Mapped[str | None] = mapped_column(String(50), nullable=True)
    room: Mapped[str | None] = mapped_column(String(80), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    enrollments = relationship("Enrollment", back_populates="classroom", cascade="all, delete-orphan")
    sessions = relationship("ClassSession", back_populates="classroom")
