from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class StudentBase(BaseModel):
    stu_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=120)
    gender: str | None = None
    qr_code: str | None = None
    qr_image_path: str | None = None
    face_dataset_path: str | None = None
    active: bool = True


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    stu_id: str | None = None
    name: str | None = None
    gender: str | None = None
    qr_code: str | None = None
    qr_image_path: str | None = None
    face_dataset_path: str | None = None
    active: bool | None = None


class StudentRead(StudentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
