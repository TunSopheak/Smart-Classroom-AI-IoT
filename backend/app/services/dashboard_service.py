from sqlalchemy.orm import Session

from app.core.constants import AttendanceStatus
from app.models.attendance_event import AttendanceEvent
from app.models.attendance_record import AttendanceRecord
from app.models.class_session import ClassSession
from app.models.student import Student


def get_dashboard_stats(db: Session) -> dict:
    active_session = (
        db.query(ClassSession)
        .filter(ClassSession.active.is_(True))
        .order_by(ClassSession.start_time.desc())
        .first()
    )

    stats = {
        "total_students": db.query(Student).filter(Student.active.is_(True)).count(),
        "present": 0,
        "late": 0,
        "absent": 0,
        "permission": 0,
        "active_sessions": db.query(ClassSession).filter(ClassSession.active.is_(True)).count(),
        "active_session": active_session,
        "recent_events": db.query(AttendanceEvent).order_by(AttendanceEvent.timestamp.desc()).limit(8).all(),
    }

    if active_session:
        records = db.query(AttendanceRecord).filter(AttendanceRecord.session_id == active_session.id).all()
        stats["present"] = sum(1 for r in records if r.status == AttendanceStatus.PRESENT.value)
        stats["late"] = sum(1 for r in records if r.status == AttendanceStatus.LATE.value)
        stats["absent"] = sum(1 for r in records if r.status == AttendanceStatus.ABSENT.value)
        stats["permission"] = sum(1 for r in records if r.status == AttendanceStatus.PERMISSION.value)

    return stats
