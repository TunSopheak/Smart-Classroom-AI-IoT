from typing import Optional

from pydantic import BaseModel, Field

from app.core.constants import AIMonitoringEventType, AIMonitoringSeverity


class AIMonitoringEventCreate(BaseModel):
    session_id: Optional[int] = None
    student_id: Optional[int] = None
    event_type: AIMonitoringEventType
    severity: AIMonitoringSeverity = AIMonitoringSeverity.INFO
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    source: str = Field(default="manual_simulation", max_length=80)
    description: Optional[str] = None


class AIMonitoringEventRead(BaseModel):
    id: int
    session_id: Optional[int]
    student_id: Optional[int]
    event_type: str
    severity: str
    confidence: Optional[float]
    source: str
    description: Optional[str]

    class Config:
        orm_mode = True
