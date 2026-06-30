from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.timezone import format_cambodia_datetime, format_cambodia_time
from app.database.database import get_db
from app.models.ai_monitoring_event import AIMonitoringEvent
from app.models.camera_recording import CameraRecording
from app.models.class_session import ClassSession
from app.schemas.ai_monitoring_schema import AIMonitoringEventCreate
from app.services.ai_monitoring_service import create_ai_monitoring_event
from app.services.camera_monitoring_service import camera_service, convert_recording_to_webm
from app.services.face_product_service import LABELS_PATH, MODEL_PATH
from app.services.iot_automation_service import get_current_occupancy_count
from app.services.iot_service import get_iot_stats, list_devices, seed_demo_devices

router = APIRouter(tags=["Camera Monitoring"])
templates = Jinja2Templates(directory="app/templates")

BACKEND_ROOT = Path(__file__).resolve().parents[2]
RECORDINGS_DIR = BACKEND_ROOT / "app" / "static" / "recordings"

BEHAVIOR_TYPES = [
    "phone_usage",
    "sleeping",
    "leaving_seat",
    "attention_low",
    "looking_around",
    "book_usage",
    "hand_raising",
    "no_face_detected",
    "unknown_face",
    "multiple_faces",
]


def build_return_url(default_path: str, session_id: Optional[int] = None, return_to: str = ""):
    if return_to and return_to.startswith("/dashboard/"):
        return return_to

    url = default_path
    if session_id:
        url += f"?session_id={session_id}"
    return url


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


def get_recording_file_path(recording: CameraRecording):
    return RECORDINGS_DIR / recording.filename


def get_recording_media_type(filename: str):
    if filename.lower().endswith(".webm"):
        return "video/webm"
    if filename.lower().endswith(".mp4"):
        return "video/mp4"
    return "application/octet-stream"


def enrich_recording_file_info(recording: CameraRecording):
    file_path = get_recording_file_path(recording)

    recording.file_exists = file_path.exists()
    recording.file_size_bytes = file_path.stat().st_size if file_path.exists() else 0
    recording.file_size_mb = round(recording.file_size_bytes / (1024 * 1024), 2)

    recording.is_webm = recording.filename.lower().endswith(".webm")
    recording.is_mp4 = recording.filename.lower().endswith(".mp4")

    recording.is_playable = recording.file_exists and recording.file_size_bytes > 100000 and recording.is_webm
    recording.is_convertible = recording.file_exists and recording.file_size_bytes > 100000 and recording.is_mp4

    recording.media_type = get_recording_media_type(recording.filename)

    return recording


@router.get("/dashboard/camera-monitoring")
def dashboard_camera_monitoring(
    request: Request,
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    sessions = db.query(ClassSession).order_by(ClassSession.start_time.desc()).limit(30).all()
    selected_session = db.query(ClassSession).filter(ClassSession.id == session_id).first() if session_id else get_active_or_latest_session(db)

    if selected_session:
        camera_service.set_session(selected_session.id)

    recordings = (
        db.query(CameraRecording)
        .order_by(CameraRecording.started_at.desc())
        .limit(20)
        .all()
    )
    recordings = [enrich_recording_file_info(item) for item in recordings]

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
            "format_kh_datetime": format_cambodia_datetime,
            "format_kh_time": format_cambodia_time,
        },
    )


@router.get("/dashboard/monitoring-workspace")
def dashboard_monitoring_workspace(
    request: Request,
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    sessions = db.query(ClassSession).order_by(ClassSession.start_time.desc()).limit(30).all()
    selected_session = db.query(ClassSession).filter(ClassSession.id == session_id).first() if session_id else get_active_or_latest_session(db)

    if selected_session:
        camera_service.set_session(selected_session.id)

    if not list_devices(db):
        seed_demo_devices(db)

    ai_events = []
    if selected_session:
        ai_events = (
            db.query(AIMonitoringEvent)
            .filter(AIMonitoringEvent.session_id == selected_session.id)
            .order_by(AIMonitoringEvent.created_at.desc())
            .limit(10)
            .all()
        )

    recordings = (
        db.query(CameraRecording)
        .order_by(CameraRecording.started_at.desc())
        .limit(6)
        .all()
    )
    recordings = [enrich_recording_file_info(item) for item in recordings]

    occupancy_count, occupancy_session = get_current_occupancy_count(db)
    devices = list_devices(db)

    return templates.TemplateResponse(
        request,
        "monitoring/workspace.html",
        {
            "request": request,
            "sessions": sessions,
            "selected_session": selected_session,
            "camera_status": camera_service.get_status(),
            "recordings": recordings,
            "ai_events": ai_events,
            "behavior_types": BEHAVIOR_TYPES,
            "model_exists": MODEL_PATH.exists(),
            "labels_exists": LABELS_PATH.exists(),
            "devices": devices,
            "iot_stats": get_iot_stats(db),
            "occupancy_count": occupancy_count,
            "occupancy_session": occupancy_session,
            "format_kh_datetime": format_cambodia_datetime,
            "format_kh_time": format_cambodia_time,
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
def dashboard_start_camera(session_id: Optional[int] = Form(None), return_to: str = Form("")):
    camera_service.set_session(session_id)
    camera_service.start(0)
    return RedirectResponse(url=build_return_url("/dashboard/camera-monitoring", session_id, return_to), status_code=303)


@router.post("/dashboard/monitoring-workspace/start")
def dashboard_start_monitoring(session_id: Optional[int] = Form(None), return_to: str = Form("")):
    camera_service.set_session(session_id)
    camera_service.start(0)
    camera_service.enable_auto_face_attendance(session_id=session_id)
    camera_service.enable_auto_behavior(session_id=session_id)
    return RedirectResponse(url=build_return_url("/dashboard/monitoring-workspace", session_id, return_to), status_code=303)


@router.post("/dashboard/monitoring-workspace/stop")
def dashboard_stop_monitoring(session_id: Optional[int] = Form(None), return_to: str = Form("")):
    camera_service.disable_auto_behavior()
    camera_service.disable_auto_face_attendance()
    camera_service.stop()
    return RedirectResponse(url=build_return_url("/dashboard/monitoring-workspace", session_id, return_to), status_code=303)


@router.post("/dashboard/camera-monitoring/stop")
def dashboard_stop_camera(session_id: Optional[int] = Form(None), return_to: str = Form("")):
    camera_service.stop()
    return RedirectResponse(url=build_return_url("/dashboard/camera-monitoring", session_id, return_to), status_code=303)


@router.post("/dashboard/camera-monitoring/behavior-auto/start")
def dashboard_start_auto_behavior(session_id: Optional[int] = Form(None), return_to: str = Form("")):
    camera_service.enable_auto_behavior(session_id=session_id)

    if not camera_service.running:
        camera_service.start(0)

    return RedirectResponse(url=build_return_url("/dashboard/camera-monitoring", session_id, return_to), status_code=303)


@router.post("/dashboard/camera-monitoring/behavior-auto/stop")
def dashboard_stop_auto_behavior(session_id: Optional[int] = Form(None), return_to: str = Form("")):
    camera_service.disable_auto_behavior()
    return RedirectResponse(url=build_return_url("/dashboard/camera-monitoring", session_id, return_to), status_code=303)


@router.post("/dashboard/camera-monitoring/face-attendance/start")
def dashboard_start_auto_face_attendance(session_id: Optional[int] = Form(None), return_to: str = Form("")):
    camera_service.enable_auto_face_attendance(session_id=session_id)
    if not camera_service.running:
        camera_service.start(0)
    return RedirectResponse(url=build_return_url("/dashboard/monitoring-workspace", session_id, return_to), status_code=303)


@router.post("/dashboard/camera-monitoring/face-attendance/stop")
def dashboard_stop_auto_face_attendance(session_id: Optional[int] = Form(None), return_to: str = Form("")):
    camera_service.disable_auto_face_attendance()
    return RedirectResponse(url=build_return_url("/dashboard/monitoring-workspace", session_id, return_to), status_code=303)


@router.post("/dashboard/camera-monitoring/record/start")
def dashboard_start_recording(
    session_id: Optional[int] = Form(None),
    return_to: str = Form(""),
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

    return RedirectResponse(url=build_return_url("/dashboard/camera-monitoring", session_id, return_to), status_code=303)




@router.post("/dashboard/camera-monitoring/record/stop")
def dashboard_stop_recording(
    session_id: Optional[int] = Form(None),
    return_to: str = Form(""),
    db: Session = Depends(get_db),
):
    result = None

    try:
        result = camera_service.stop_recording()
    except Exception as exc:
        print(f"Safe stop caught recording error: {exc}")

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
    else:
        # Recovery fallback: if stop crashed after file was written,
        # mark the latest valid recording as saved.
        latest = (
            db.query(CameraRecording)
            .filter(CameraRecording.status == "recording")
            .order_by(CameraRecording.started_at.desc())
            .first()
        )

        if latest:
            file_path = get_recording_file_path(latest)
            if file_path.exists() and file_path.stat().st_size > 100000:
                latest.status = "saved"
                latest.stopped_at = datetime.utcnow()
                if latest.started_at:
                    latest.duration_seconds = (latest.stopped_at - latest.started_at).total_seconds()
                db.commit()

    return RedirectResponse(url=build_return_url("/dashboard/camera-monitoring", session_id, return_to), status_code=303)

@router.post("/dashboard/camera-monitoring/behavior")
def dashboard_log_behavior(
    session_id: Optional[int] = Form(None),
    event_type: str = Form(...),
    severity: str = Form("medium"),
    return_to: str = Form(""),
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

    return RedirectResponse(url=build_return_url("/dashboard/camera-monitoring", session_id, return_to), status_code=303)




@router.post("/dashboard/camera-monitoring/recordings/fix-stuck")
def dashboard_fix_stuck_recordings(
    session_id: Optional[int] = Form(None),
    return_to: str = Form(""),
    db: Session = Depends(get_db),
):
    stuck_recordings = (
        db.query(CameraRecording)
        .filter(CameraRecording.status == "recording")
        .order_by(CameraRecording.started_at.desc())
        .all()
    )

    fixed_count = 0

    for item in stuck_recordings:
        file_path = get_recording_file_path(item)

        if file_path.exists() and file_path.stat().st_size > 100000:
            item.status = "saved"
            item.stopped_at = datetime.utcnow()
            if item.started_at:
                item.duration_seconds = (item.stopped_at - item.started_at).total_seconds()
            fixed_count += 1

    db.commit()
    print(f"Fixed stuck recordings: {fixed_count}")

    return RedirectResponse(url=build_return_url("/dashboard/camera-monitoring", session_id, return_to), status_code=303)


@router.get("/dashboard/camera-monitoring/recordings/{recording_id}")
def dashboard_recording_playback(
    recording_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    recording = db.query(CameraRecording).filter(CameraRecording.id == recording_id).first()
    recording = enrich_recording_file_info(recording) if recording else None

    return templates.TemplateResponse(
        request,
        "camera_monitoring/playback.html",
        {
            "request": request,
            "recording": recording,
            "format_kh_datetime": format_cambodia_datetime,
            "format_kh_time": format_cambodia_time,
        },
    )


@router.post("/dashboard/camera-monitoring/recordings/{recording_id}/convert-webm")
def dashboard_convert_recording_to_webm(
    recording_id: int,
    db: Session = Depends(get_db),
):
    recording = db.query(CameraRecording).filter(CameraRecording.id == recording_id).first()

    if not recording:
        return RedirectResponse(url="/dashboard/camera-monitoring", status_code=303)

    source_path = get_recording_file_path(recording)
    result = convert_recording_to_webm(source_path)

    if not result:
        return RedirectResponse(url=f"/dashboard/camera-monitoring/recordings/{recording_id}", status_code=303)

    new_recording = CameraRecording(
        session_id=recording.session_id,
        filename=result["filename"],
        file_path=f"/static/recordings/{result['filename']}",
        status="saved",
        started_at=datetime.utcnow(),
        stopped_at=datetime.utcnow(),
        duration_seconds=result.get("duration_seconds"),
        note=f"Converted from legacy recording: {recording.filename}",
    )

    db.add(new_recording)
    db.commit()
    db.refresh(new_recording)

    return RedirectResponse(
        url=f"/dashboard/camera-monitoring/recordings/{new_recording.id}",
        status_code=303,
    )




@router.get("/dashboard/camera-monitoring/recordings/{recording_id}/stream")
def dashboard_recording_stream(
    recording_id: int,
    db: Session = Depends(get_db),
):
    recording = db.query(CameraRecording).filter(CameraRecording.id == recording_id).first()

    if not recording:
        return {"success": False, "message": "Recording not found."}

    file_path = get_recording_file_path(recording)

    if not file_path.exists():
        return {"success": False, "message": "Recording file is missing from storage."}

    return FileResponse(
        path=str(file_path),
        media_type=get_recording_media_type(recording.filename),
    )


@router.get("/dashboard/camera-monitoring/recordings/{recording_id}/download")
def dashboard_recording_download(
    recording_id: int,
    db: Session = Depends(get_db),
):
    recording = db.query(CameraRecording).filter(CameraRecording.id == recording_id).first()

    if not recording:
        return {"success": False, "message": "Recording not found."}

    file_path = get_recording_file_path(recording)

    if not file_path.exists():
        return {"success": False, "message": "Recording file is missing from storage."}

    return FileResponse(
        path=str(file_path),
        filename=recording.filename,
        media_type=get_recording_media_type(recording.filename),
    )


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
