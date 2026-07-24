from datetime import datetime

from pydantic import BaseModel, Field


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
