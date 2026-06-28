from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AIEvent(Base):
    __tablename__ = "ai_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id"), nullable=False)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
