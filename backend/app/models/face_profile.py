from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class FaceProfile(Base):
    __tablename__ = "face_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    dataset_path: Mapped[str] = mapped_column(String(255), nullable=False)
    model_label: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
