from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud.classroom_crud import create_classroom, get_classroom_students, get_classrooms
from app.database.database import get_db
from app.schemas.classroom_schema import ClassroomCreate, ClassroomRead
from app.schemas.student_schema import StudentRead

router = APIRouter(prefix="/api/classes", tags=["Classes"])


@router.get("", response_model=list[ClassroomRead])
def list_classes(db: Session = Depends(get_db)):
    return get_classrooms(db)


@router.post("", response_model=ClassroomRead)
def create_class(data: ClassroomCreate, db: Session = Depends(get_db)):
    return create_classroom(db, data)


@router.get("/{class_id}/students", response_model=list[StudentRead])
def list_class_students(class_id: int, db: Session = Depends(get_db)):
    return get_classroom_students(db, class_id)
