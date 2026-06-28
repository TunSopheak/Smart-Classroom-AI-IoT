from sqlalchemy.orm import Session

from app.models.class_session import ClassSession
from app.schemas.session_schema import ClassSessionCreate, ClassSessionUpdate


def get_sessions(db: Session):
    return db.query(ClassSession).order_by(ClassSession.start_time.desc()).all()


def get_session(db: Session, session_id: int):
    return db.query(ClassSession).filter(ClassSession.id == session_id).first()


def create_session(db: Session, data: ClassSessionCreate):
    session = ClassSession(**data.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_session(db: Session, session: ClassSession, data: ClassSessionUpdate):
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(session, key, value)
    db.commit()
    db.refresh(session)
    return session
