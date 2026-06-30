from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator


class ClassSessionBase(BaseModel):
    classroom_id: int
    subject_id: int
    class_group_id: int | None = None
    course_id: int | None = None
    weekly_schedule_id: int | None = None
    title: str
    start_time: datetime
    late_time: datetime
    close_time: datetime
    active: bool = True

    @model_validator(mode="after")
    def validate_time_order(self):
        if self.late_time < self.start_time:
            raise ValueError("late_time must be after or equal to start_time")
        if self.close_time <= self.late_time:
            raise ValueError("close_time must be after late_time")
        return self


class ClassSessionCreate(ClassSessionBase):
    created_by: int | None = None


class ClassSessionUpdate(BaseModel):
    title: str | None = None
    start_time: datetime | None = None
    late_time: datetime | None = None
    close_time: datetime | None = None
    active: bool | None = None


class ClassSessionRead(ClassSessionBase):
    id: int
    created_by: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
