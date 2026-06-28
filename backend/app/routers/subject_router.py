from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.subject import Subject
from app.schemas.subject_schema import SubjectCreate, SubjectRead

router = APIRouter(prefix="/api/subjects", tags=["Subjects"])


@router.get("", response_model=list[SubjectRead])
def list_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).order_by(Subject.id).all()


@router.post("", response_model=SubjectRead)
def create_subject(data: SubjectCreate, db: Session = Depends(get_db)):
    subject = Subject(**data.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject
