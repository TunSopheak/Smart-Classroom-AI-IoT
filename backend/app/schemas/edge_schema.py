from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.constants import AIMonitoringEventType, AIMonitoringSeverity


DEVICE_ID_PATTERN = r"^[A-Za-z0-9._:-]+$"
SHA256_PATTERN = r"^[A-Fa-f0-9]{64}$"


class EdgeHeartbeatRequest(BaseModel):
    device_id: str = Field(
        min_length=3,
        max_length=80,
        pattern=DEVICE_ID_PATTERN,
    )
    agent_version: str = Field(
        min_length=1,
        max_length=40,
    )
    local_timestamp: datetime

    camera_ready: bool
    face_model_ready: bool
    object_model_ready: bool
    ai_pipeline_ready: bool

    trained_identity_count: int = Field(
        default=0,
        ge=0,
        le=100000,
    )
    face_model_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    object_model_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )


class EdgeStudentContext(BaseModel):
    stu_id: str
    name: str


class EdgeSessionContext(BaseModel):
    session_id: int
    title: str
    start_time: datetime
    late_time: datetime
    close_time: datetime
    students: list[EdgeStudentContext]


class EdgeContextResponse(BaseModel):
    api_version: str
    server_timestamp: datetime
    attendance_face_threshold: float
    active_session: EdgeSessionContext | None


class EdgeBoundingBox(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class EdgeObjectDetection(BaseModel):
    class_name: str = Field(min_length=1, max_length=80)
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: EdgeBoundingBox | None = None


class EdgeBehaviorEvent(BaseModel):
    event_type: AIMonitoringEventType
    severity: AIMonitoringSeverity = AIMonitoringSeverity.INFO
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    description: str | None = Field(default=None, max_length=500)


class EdgeInferenceEventRequest(BaseModel):
    event_id: UUID
    device_id: str = Field(
        min_length=3,
        max_length=80,
        pattern=DEVICE_ID_PATTERN,
    )
    session_id: int = Field(gt=0)
    captured_at: datetime

    face_status: Literal["recognized", "unknown", "no_face"]
    stu_id: str | None = Field(default=None, min_length=1, max_length=50)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    lbph_distance: float | None = Field(default=None, ge=0.0)
    stable_frame_count: int = Field(default=0, ge=0, le=10000)
    attendance_requested: bool = True
    face_bbox: EdgeBoundingBox | None = None

    object_detections: list[EdgeObjectDetection] = Field(
        default_factory=list,
        max_length=100,
    )
    behavior_events: list[EdgeBehaviorEvent] = Field(
        default_factory=list,
        max_length=100,
    )

    @model_validator(mode="after")
    def validate_face_identity(self):
        if self.face_status == "recognized":
            if not self.stu_id:
                raise ValueError(
                    "stu_id is required when face_status is recognized."
                )
            if self.confidence is None:
                raise ValueError(
                    "confidence is required when face_status is recognized."
                )
            if self.lbph_distance is None:
                raise ValueError(
                    "lbph_distance is required when face_status is recognized."
                )
        elif self.stu_id is not None:
            raise ValueError(
                "stu_id must be omitted unless face_status is recognized."
            )
        return self


class EdgeInferenceEventResponse(BaseModel):
    success: bool
    duplicate: bool
    event_id: UUID
    processing_status: str
    face_status: str
    attendance_recorded: bool
    attendance_result: str | None
    attendance_record_id: int | None
    attendance_event_id: int | None
    ai_monitoring_event_ids: list[int]
    object_detection_count: int
    behavior_event_count: int
    message: str
