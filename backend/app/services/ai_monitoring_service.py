from sqlalchemy.orm import Session

from app.models.ai_monitoring_event import AIMonitoringEvent
from app.models.class_session import ClassSession
from app.models.student import Student
from app.schemas.ai_monitoring_schema import AIMonitoringEventCreate
from app.services.attendance_service import is_student_enrolled


def _payload_to_dict(payload: AIMonitoringEventCreate) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    return payload.dict()


def _validate_event_scope(db: Session, data: dict) -> None:
    session_id = data.get("session_id")
    student_id = data.get("student_id")

    session = None
    if session_id is not None:
        session = db.get(ClassSession, session_id)
        if not session:
            raise ValueError("Session not found.")

    if student_id is not None:
        student = db.get(Student, student_id)
        if not student or not student.active:
            raise ValueError("Student not found or inactive.")

        if session:
            if not is_student_enrolled(db, session, student_id):
                raise ValueError("Student is not enrolled in this session class/group.")


def create_ai_monitoring_event(db: Session, payload: AIMonitoringEventCreate) -> AIMonitoringEvent:
    data = _payload_to_dict(payload)
    _validate_event_scope(db, data)

    confidence = data.get("confidence")
    if confidence is not None:
        confidence = round(float(confidence), 2)

    event = AIMonitoringEvent(
        session_id=data.get("session_id"),
        student_id=data.get("student_id"),
        event_type=str(data.get("event_type")).strip().lower(),
        severity=str(data.get("severity") or "info").strip().lower(),
        confidence=confidence,
        source=str(data.get("source") or "manual_simulation").strip(),
        description=data.get("description"),
    )

    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_ai_monitoring_events(
    db: Session,
    session_id: int | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    limit: int = 100,
):
    query = db.query(AIMonitoringEvent)

    if session_id:
        query = query.filter(AIMonitoringEvent.session_id == session_id)

    if event_type:
        query = query.filter(AIMonitoringEvent.event_type == event_type)

    if severity:
        query = query.filter(AIMonitoringEvent.severity == severity)

    return query.order_by(AIMonitoringEvent.created_at.desc()).limit(limit).all()


def get_ai_monitoring_stats(events):
    stats = {
        "total": len(events),
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
        "phone_usage": 0,
        "sleeping": 0,
        "leaving_seat": 0,
        "hand_raising": 0,
        "attention_low": 0,
    }

    for event in events:
        severity = (event.severity or "info").lower()
        event_type = (event.event_type or "").lower()

        if severity in stats:
            stats[severity] += 1

        if event_type in stats:
            stats[event_type] += 1

    return stats
