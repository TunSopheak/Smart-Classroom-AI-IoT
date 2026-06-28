from sqlalchemy.orm import Session

from app.models.classroom import Classroom
from app.models.enrollment import Enrollment
from app.schemas.classroom_schema import ClassroomCreate


def get_classrooms(db: Session):
    return db.query(Classroom).order_by(Classroom.id).all()


def create_classroom(db: Session, data: ClassroomCreate):
    classroom = Classroom(**data.model_dump())
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return classroom


def get_classroom_students(db: Session, classroom_id: int):
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.classroom_id == classroom_id, Enrollment.active.is_(True))
        .all()
    )
    return [enrollment.student for enrollment in enrollments]
