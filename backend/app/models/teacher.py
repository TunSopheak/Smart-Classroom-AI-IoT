from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="teacher_profile")
    subjects = relationship("Subject", back_populates="teacher")
