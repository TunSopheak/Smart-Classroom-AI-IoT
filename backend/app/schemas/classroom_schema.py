from pydantic import BaseModel, ConfigDict


class ClassroomBase(BaseModel):
    code: str
    name: str
    section: str | None = None
    shift: str | None = None
    room: str | None = None
    active: bool = True


class ClassroomCreate(ClassroomBase):
    pass


class ClassroomRead(ClassroomBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
