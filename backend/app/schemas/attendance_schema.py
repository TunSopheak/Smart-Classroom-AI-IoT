from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import AttendanceMethod, AttendanceStatus


class AttendanceRecordRead(BaseModel):
    id: int
    session_id: int
    student_id: int
    first_seen_time: datetime | None = None
    status: AttendanceStatus
    method: AttendanceMethod
    confidence: float | None = None
    overridden_by: int | None = None
    override_reason: str | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceOverrideRequest(BaseModel):
    status: AttendanceStatus
    overridden_by: int
    override_reason: str = Field(min_length=3)


class QRScanRequest(BaseModel):
    qr_code: str = Field(min_length=1)
    session_id: int | None = None
    raw_source: str = "api_qr_scan"


class AttendanceScanResponse(BaseModel):
    ok: bool
    message: str
    result: str
    student_id: int | None = None
    record_id: int | None = None
    event_id: int | None = None
    status: AttendanceStatus | None = None


class AttendanceEventRead(BaseModel):
    id: int
    session_id: int
    student_id: int | None = None
    timestamp: datetime
    method: str
    confidence: float | None = None
    raw_source: str | None = None
    result: str
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)
