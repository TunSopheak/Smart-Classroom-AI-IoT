from sqlalchemy.orm import Session

from app.models.student import Student
from app.schemas.student_schema import StudentCreate, StudentUpdate


def get_students(db: Session, skip: int = 0, limit: int = 200):
    return db.query(Student).order_by(Student.id).offset(skip).limit(limit).all()


def get_active_students(db: Session):
    return db.query(Student).filter(Student.active.is_(True)).order_by(Student.id).all()


def get_student(db: Session, student_id: int):
    return db.query(Student).filter(Student.id == student_id).first()


def get_student_by_stu_id(db: Session, stu_id: str):
    return db.query(Student).filter(Student.stu_id == stu_id).first()


def get_student_by_qr_code(db: Session, qr_code: str):
    return db.query(Student).filter(Student.qr_code == qr_code).first()


def create_student(db: Session, data: StudentCreate):
    student = Student(**data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def update_student(db: Session, student: Student, data: StudentUpdate):
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(student, key, value)
    db.commit()
    db.refresh(student)
    return student


def deactivate_student(db: Session, student: Student):
    student.active = False
    db.commit()
    db.refresh(student)
    return student


def activate_student(db: Session, student: Student):
    student.active = True
    db.commit()
    db.refresh(student)
    return student
