from sqlalchemy.orm import Session

from app.models.attendance_event import AttendanceEvent
from app.models.attendance_record import AttendanceRecord


def get_attendance_records(db: Session, session_id: int):
    return (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == session_id)
        .order_by(AttendanceRecord.student_id)
        .all()
    )


def get_attendance_record(db: Session, record_id: int):
    return db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()


def get_attendance_events(db: Session, session_id: int):
    return (
        db.query(AttendanceEvent)
        .filter(AttendanceEvent.session_id == session_id)
        .order_by(AttendanceEvent.timestamp.desc())
        .all()
    )
