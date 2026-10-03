from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class EdgeInferenceEvent(Base):
    __tablename__ = "edge_inference_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    device_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("class_sessions.id"), index=True, nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    face_status: Mapped[str] = mapped_column(String(20), nullable=False)
    stu_id: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    lbph_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    stable_frame_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    face_bbox_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_detections_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    behavior_events_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)

    processing_status: Mapped[str] = mapped_column(
        String(20), default="processing", index=True, nullable=False
    )
    attendance_result: Mapped[str | None] = mapped_column(String(40), nullable=True)
    attendance_record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attendance_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
