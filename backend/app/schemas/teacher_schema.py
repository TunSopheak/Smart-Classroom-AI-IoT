from pydantic import BaseModel, ConfigDict


class TeacherBase(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    active: bool = True


class TeacherCreate(TeacherBase):
    user_id: int | None = None


class TeacherRead(TeacherBase):
    id: int
    user_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
