from sqlalchemy.orm import Session

from app.models.ai_monitoring_event import AIMonitoringEvent
from app.schemas.ai_monitoring_schema import AIMonitoringEventCreate


def _payload_to_dict(payload: AIMonitoringEventCreate) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


def create_ai_monitoring_event(db: Session, payload: AIMonitoringEventCreate) -> AIMonitoringEvent:
    data = _payload_to_dict(payload)

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


def list_ai_monitoring_events(db: Session, session_id: int | None = None, limit: int = 100):
    query = db.query(AIMonitoringEvent)

    if session_id:
        query = query.filter(AIMonitoringEvent.session_id == session_id)

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
