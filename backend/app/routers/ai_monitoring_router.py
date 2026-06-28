from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.class_session import ClassSession
from app.models.student import Student
from app.schemas.ai_monitoring_schema import AIMonitoringEventCreate
from app.services.ai_monitoring_service import (
    create_ai_monitoring_event,
    get_ai_monitoring_stats,
    list_ai_monitoring_events,
)

router = APIRouter(tags=["AI Monitoring"])
templates = Jinja2Templates(directory="app/templates")

EVENT_TYPES = [
    "phone_usage",
    "sleeping",
    "leaving_seat",
    "hand_raising",
    "attention_low",
]

SEVERITIES = [
    "info",
    "low",
    "medium",
    "high",
]


def event_to_dict(event):
    return {
        "id": event.id,
        "session_id": event.session_id,
        "student_id": event.student_id,
        "student": {
            "id": event.student.id,
            "stu_id": event.student.stu_id,
            "name": event.student.name,
        } if event.student else None,
        "event_type": event.event_type,
        "severity": event.severity,
        "confidence": event.confidence,
        "source": event.source,
        "description": event.description,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.get("/api/ai-monitoring/events")
def api_list_ai_events(
    session_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    events = list_ai_monitoring_events(db, session_id=session_id, limit=limit)
    return [event_to_dict(event) for event in events]


@router.post("/api/ai-monitoring/events")
def api_create_ai_event(
    payload: AIMonitoringEventCreate,
    db: Session = Depends(get_db),
):
    event = create_ai_monitoring_event(db, payload)
    return {
        "success": True,
        "message": "AI monitoring event logged successfully.",
        "event": event_to_dict(event),
    }


@router.post("/api/ai-monitoring/simulate")
def api_simulate_ai_event(
    payload: AIMonitoringEventCreate,
    db: Session = Depends(get_db),
):
    event = create_ai_monitoring_event(db, payload)
    return {
        "success": True,
        "message": f"Simulated AI event: {event.event_type}",
        "event": event_to_dict(event),
    }


@router.get("/dashboard/ai-monitoring")
def dashboard_ai_monitoring(
    request: Request,
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ClassSession)
        .order_by(ClassSession.start_time.desc())
        .limit(20)
        .all()
    )

    active_session = (
        db.query(ClassSession)
        .filter(ClassSession.active == True)
        .order_by(ClassSession.start_time.desc())
        .first()
    )

    selected_session_id = session_id
    if selected_session_id is None and active_session:
        selected_session_id = active_session.id
    elif selected_session_id is None and sessions:
        selected_session_id = sessions[0].id

    students = db.query(Student).order_by(Student.stu_id.asc()).all()

    events = list_ai_monitoring_events(
        db,
        session_id=selected_session_id,
        limit=100,
    )

    stats = get_ai_monitoring_stats(events)

    return templates.TemplateResponse(
        request,
        "ai_monitoring/index.html",
        {
            "request": request,
            "sessions": sessions,
            "students": students,
            "events": events,
            "stats": stats,
            "event_types": EVENT_TYPES,
            "severities": SEVERITIES,
            "selected_session_id": selected_session_id,
            "active_session": active_session,
        },
    )


@router.post("/dashboard/ai-monitoring/simulate")
def dashboard_simulate_ai_event(
    session_id: int = Form(...),
    student_id: str = Form(""),
    event_type: str = Form(...),
    severity: str = Form("info"),
    confidence: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    parsed_student_id = int(student_id) if student_id else None

    parsed_confidence = None
    if confidence:
        try:
            parsed_confidence = float(confidence)
        except ValueError:
            parsed_confidence = None

    payload = AIMonitoringEventCreate(
        session_id=session_id,
        student_id=parsed_student_id,
        event_type=event_type,
        severity=severity,
        confidence=parsed_confidence,
        source="dashboard_manual_simulation",
        description=description or f"Manual simulation for {event_type}",
    )

    create_ai_monitoring_event(db, payload)

    return RedirectResponse(
        url=f"/dashboard/ai-monitoring?session_id={session_id}",
        status_code=303,
    )
