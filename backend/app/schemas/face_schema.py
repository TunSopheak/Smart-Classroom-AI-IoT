from pydantic import BaseModel, Field


class FaceRecognitionRequest(BaseModel):
    student_id: int
    session_id: int | None = None
    confidence: float = Field(default=0.86, ge=0.0, le=1.0)
    raw_source: str = "api_face_recognition_simulation"
