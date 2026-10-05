from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.core.timezone import utc_now


class EdgeDevice(Base):
    """Latest heartbeat state reported by a real AI Edge Agent."""

    __tablename__ = "edge_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(40), nullable=False)

    camera_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    face_model_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    object_model_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_pipeline_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trained_identity_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    face_model_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    object_model_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    last_seen_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
