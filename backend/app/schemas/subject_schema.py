from pydantic import BaseModel, ConfigDict


class SubjectBase(BaseModel):
    code: str
    name: str
    teacher_id: int | None = None
    active: bool = True


class SubjectCreate(SubjectBase):
    pass


class SubjectRead(SubjectBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
