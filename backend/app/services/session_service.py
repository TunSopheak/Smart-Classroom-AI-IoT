from sqlalchemy.orm import Session

from app.models.class_session import ClassSession
from app.services.attendance_service import ensure_attendance_records_for_session


def prepare_session_attendance(db: Session, session: ClassSession):
    return ensure_attendance_records_for_session(db, session)
