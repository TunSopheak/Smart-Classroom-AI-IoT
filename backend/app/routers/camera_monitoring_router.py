from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.ai_monitoring_event import AIMonitoringEvent
from app.models.camera_recording import CameraRecording
from app.models.class_session import ClassSession
from app.schemas.ai_monitoring_schema import AIMonitoringEventCreate
from app.services.ai_monitoring_service import create_ai_monitoring_event
from app.services.camera_monitoring_service import camera_service

router = APIRouter(tags=["Camera Monitoring"])
templates = Jinja2Templates(directory="app/templates")


BEHAVIOR_TYPES = [
    "phone_usage",
    "sleeping",
    "leaving_seat",
    "attention_low",
    "hand_raising",
]


def get_active_or_latest_session(db: Session):
    active = (
        db.query(ClassSession)
        .filter(ClassSession.active == True)
        .order_by(ClassSession.start_time.desc())
        .first()
    )

    if active:
        return active

    return db.query(ClassSession).order_by(ClassSession.start_time.desc()).first()


@router.get("/dashboard/camera-monitoring")
def dashboard_camera_monitoring(
    request: Request,
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    sessions = db.query(ClassSession).order_by(ClassSession.start_time.desc()).limit(30).all()
    selected_session = db.query(ClassSession).filter(ClassSession.id == session_id).first() if session_id else get_active_or_latest_session(db)

    recordings = (
        db.query(CameraRecording)
        .order_by(CameraRecording.started_at.desc())
        .limit(20)
        .all()
    )

    ai_events = []
    if selected_session:
        ai_events = (
            db.query(AIMonitoringEvent)
            .filter(AIMonitoringEvent.session_id == selected_session.id)
            .order_by(AIMonitoringEvent.created_at.desc())
            .limit(10)
            .all()
        )

    return templates.TemplateResponse(
        request,
        "camera_monitoring/index.html",
        {
            "request": request,
            "sessions": sessions,
            "selected_session": selected_session,
            "camera_status": camera_service.get_status(),
            "recordings": recordings,
            "ai_events": ai_events,
            "behavior_types": BEHAVIOR_TYPES,
        },
    )


@router.get("/api/camera-monitoring/status")
def api_camera_status():
    return camera_service.get_status()


@router.get("/api/camera-monitoring/stream")
def api_camera_stream():
    return StreamingResponse(
        camera_service.frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.post("/dashboard/camera-monitoring/start")
def dashboard_start_camera(
    session_id: Optional[int] = Form(None),
):
    camera_service.start(0)

    url = "/dashboard/camera-monitoring"
    if session_id:
        url += f"?session_id={session_id}"

    return RedirectResponse(url=url, status_code=303)


@router.post("/dashboard/camera-monitoring/stop")
def dashboard_stop_camera(
    session_id: Optional[int] = Form(None),
):
    camera_service.stop()

    url = "/dashboard/camera-monitoring"
    if session_id:
        url += f"?session_id={session_id}"

    return RedirectResponse(url=url, status_code=303)


@router.post("/dashboard/camera-monitoring/record/start")
def dashboard_start_recording(
    session_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    result = camera_service.start_recording(session_id=session_id)

    if result and not result.get("already_recording"):
        recording = CameraRecording(
            session_id=session_id,
            filename=result["filename"],
            file_path=f"/static/recordings/{result['filename']}",
            status="recording",
            started_at=result["started_at"],
            note="Recording includes OpenCV frame boxes and behavior overlays.",
        )
        db.add(recording)
        db.commit()
        db.refresh(recording)

    url = "/dashboard/camera-monitoring"
    if session_id:
        url += f"?session_id={session_id}"

    return RedirectResponse(url=url, status_code=303)


@router.post("/dashboard/camera-monitoring/record/stop")
def dashboard_stop_recording(
    session_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    result = camera_service.stop_recording()

    if result and result.get("filename"):
        recording = (
            db.query(CameraRecording)
            .filter(CameraRecording.filename == result["filename"])
            .order_by(CameraRecording.started_at.desc())
            .first()
        )

        if recording:
            recording.status = "saved"
            recording.stopped_at = result["stopped_at"]
            recording.duration_seconds = result["duration_seconds"]
            db.commit()

    url = "/dashboard/camera-monitoring"
    if session_id:
        url += f"?session_id={session_id}"

    return RedirectResponse(url=url, status_code=303)


@router.post("/dashboard/camera-monitoring/behavior")
def dashboard_log_behavior(
    session_id: Optional[int] = Form(None),
    event_type: str = Form(...),
    severity: str = Form("medium"),
    db: Session = Depends(get_db),
):
    payload = AIMonitoringEventCreate(
        session_id=session_id,
        student_id=None,
        event_type=event_type,
        severity=severity,
        confidence=0.85,
        source="camera_monitoring_manual_behavior",
        description=f"Behavior event marked during live camera monitoring: {event_type}",
    )

    create_ai_monitoring_event(db, payload)
    camera_service.set_behavior_overlay(event_type=event_type, severity=severity)

    url = "/dashboard/camera-monitoring"
    if session_id:
        url += f"?session_id={session_id}"

    return RedirectResponse(url=url, status_code=303)


@router.get("/api/camera-monitoring/recordings")
def api_recordings(db: Session = Depends(get_db)):
    recordings = (
        db.query(CameraRecording)
        .order_by(CameraRecording.started_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": item.id,
            "session_id": item.session_id,
            "filename": item.filename,
            "file_path": item.file_path,
            "status": item.status,
            "started_at": item.started_at.isoformat() if item.started_at else None,
            "stopped_at": item.stopped_at.isoformat() if item.stopped_at else None,
            "duration_seconds": item.duration_seconds,
        }
        for item in recordings
    ]
