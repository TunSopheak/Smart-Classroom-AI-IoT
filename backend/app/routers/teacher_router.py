from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.teacher import Teacher
from app.schemas.teacher_schema import TeacherCreate, TeacherRead

router = APIRouter(prefix="/api/teachers", tags=["Teachers"])


@router.get("", response_model=list[TeacherRead])
def list_teachers(db: Session = Depends(get_db)):
    return db.query(Teacher).order_by(Teacher.id).all()


@router.post("", response_model=TeacherRead)
def create_teacher(data: TeacherCreate, db: Session = Depends(get_db)):
    teacher = Teacher(**data.model_dump())
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher
