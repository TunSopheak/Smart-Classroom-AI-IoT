from pathlib import Path

ROOT = Path(__file__).resolve().parent

def write_file(relative_path: str, content: str):
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Written: {path}")

write_file("app/services/camera_monitoring_service.py", r"""
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


BACKEND_ROOT = Path(__file__).resolve().parents[2]
RECORDINGS_DIR = BACKEND_ROOT / "app" / "static" / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

FRAME_WIDTH = 960
FRAME_HEIGHT = 540
FRAME_FPS = 20.0


class CameraMonitoringService:
    def __init__(self):
        self.cap = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        self.latest_frame = None
        self.camera_index = 0

        self.recording = False
        self.video_writer = None
        self.recording_path = None
        self.recording_started_at = None

        self.last_behavior = None
        self.last_behavior_time = 0

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def start(self, camera_index: int = 0):
        if self.running:
            return True

        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

        if not self.cap or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(camera_index)

        if not self.cap or not self.cap.isOpened():
            self.running = False
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, FRAME_FPS)

        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.stop_recording()
        self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.5)

        if self.cap:
            self.cap.release()
            self.cap = None

        with self.lock:
            self.latest_frame = None

        return True

    def _capture_loop(self):
        while self.running:
            ok, frame = self.cap.read()

            if not ok or frame is None:
                frame = self._blank_frame("Camera frame not available")

            annotated = self._annotate_frame(frame)
            annotated = cv2.resize(annotated, (FRAME_WIDTH, FRAME_HEIGHT))

            with self.lock:
                self.latest_frame = annotated.copy()

            if self.recording and self.video_writer is not None:
                try:
                    self.video_writer.write(annotated)
                except Exception as exc:
                    print(f"Recording write error: {exc}")

            time.sleep(1 / FRAME_FPS)

    def _blank_frame(self, message: str):
        frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        cv2.putText(frame, message, (70, 260), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
        return frame

    def _annotate_frame(self, frame):
        frame = frame.copy()
        h, w = frame.shape[:2]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(60, 60),
        )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cv2.rectangle(frame, (0, 0), (w, 46), (15, 23, 42), -1)
        cv2.putText(
            frame,
            f"Smart Classroom AI Monitoring | {timestamp}",
            (18, 31),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (255, 255, 255),
            2,
        )

        if len(faces) > 0:
            for idx, (x, y, fw, fh) in enumerate(faces, start=1):
                cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 3)
                cv2.putText(
                    frame,
                    f"Face #{idx}",
                    (x, max(35, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.78,
                    (0, 255, 0),
                    2,
                )
        else:
            cv2.rectangle(frame, (30, 65), (390, 115), (0, 0, 255), 2)
            cv2.putText(
                frame,
                "No face detected / attention check",
                (45, 98),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.72,
                (0, 0, 255),
                2,
            )

        if self.recording:
            cv2.circle(frame, (w - 145, 24), 10, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (w - 125, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (0, 0, 255), 2)

        if self.last_behavior and time.time() - self.last_behavior_time <= 8:
            label = self.last_behavior.get("event_type", "behavior")
            severity = self.last_behavior.get("severity", "info")
            color = (0, 0, 255) if severity == "high" else (0, 165, 255)

            cv2.rectangle(frame, (30, h - 92), (w - 30, h - 25), color, -1)
            cv2.putText(
                frame,
                f"Behavior Event: {label} | Severity: {severity}",
                (50, h - 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.85,
                (255, 255, 255),
                2,
            )

        return frame

    def set_behavior_overlay(self, event_type: str, severity: str = "info"):
        self.last_behavior = {
            "event_type": event_type,
            "severity": severity,
        }
        self.last_behavior_time = time.time()

    def start_recording(self, session_id: int | None = None):
        if not self.running:
            started = self.start(0)
            if not started:
                return None

        if self.recording:
            return {
                "already_recording": True,
                "path": str(self.recording_path),
                "filename": self.recording_path.name if self.recording_path else None,
                "started_at": self.recording_started_at,
            }

        # Browser-compatible recording format.
        # WebM + VP8 is much more reliable for in-browser playback than OpenCV mp4v/mp4.
        filename = f"camera_session_{session_id or 'none'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
        path = RECORDINGS_DIR / filename

        fourcc = cv2.VideoWriter_fourcc(*"VP80")
        self.video_writer = cv2.VideoWriter(str(path), fourcc, FRAME_FPS, (FRAME_WIDTH, FRAME_HEIGHT))

        if not self.video_writer or not self.video_writer.isOpened():
            self.video_writer = None
            print("ERROR: Could not open WebM VideoWriter with VP80.")
            return None

        self.recording = True
        self.recording_path = path
        self.recording_started_at = datetime.utcnow()

        return {
            "already_recording": False,
            "path": str(path),
            "filename": filename,
            "started_at": self.recording_started_at,
        }

    def stop_recording(self):
        if not self.recording:
            return None

        stopped_at = datetime.utcnow()
        duration = None

        if self.recording_started_at:
            duration = (stopped_at - self.recording_started_at).total_seconds()

        self.recording = False

        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

        result = {
            "path": str(self.recording_path) if self.recording_path else None,
            "filename": self.recording_path.name if self.recording_path else None,
            "started_at": self.recording_started_at,
            "stopped_at": stopped_at,
            "duration_seconds": duration,
        }

        if self.recording_path and self.recording_path.exists():
            print(f"Recording saved: {self.recording_path}")
            print(f"Recording size: {self.recording_path.stat().st_size} bytes")

        self.recording_path = None
        self.recording_started_at = None

        return result

    def get_status(self):
        return {
            "running": self.running,
            "recording": self.recording,
            "camera_index": self.camera_index,
            "recording_path": str(self.recording_path) if self.recording_path else None,
            "frame_width": FRAME_WIDTH,
            "frame_height": FRAME_HEIGHT,
            "format": "webm_vp8",
        }

    def get_jpeg_bytes(self):
        with self.lock:
            frame = self.latest_frame.copy() if self.latest_frame is not None else None

        if frame is None:
            frame = self._blank_frame("Camera not started. Click Start Camera.")

        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            return b""

        return buffer.tobytes()

    def frame_generator(self):
        while True:
            frame = self.get_jpeg_bytes()
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            time.sleep(0.05)


def convert_recording_to_webm(source_path: Path):
    if not source_path.exists():
        return None

    output_path = source_path.with_name(f"converted_{source_path.stem}.webm")

    cap = cv2.VideoCapture(str(source_path))
    if not cap or not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 1:
        fps = FRAME_FPS

    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"VP80"),
        fps,
        (FRAME_WIDTH, FRAME_HEIGHT),
    )

    if not writer or not writer.isOpened():
        cap.release()
        return None

    frames = 0

    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            break

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        writer.write(frame)
        frames += 1

    cap.release()
    writer.release()

    if frames <= 0:
        if output_path.exists():
            output_path.unlink()
        return None

    return {
        "filename": output_path.name,
        "path": str(output_path),
        "duration_seconds": frames / fps if fps else None,
        "frames": frames,
    }


camera_service = CameraMonitoringService()
""")

write_file("app/routers/camera_monitoring_router.py", r"""
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.ai_monitoring_event import AIMonitoringEvent
from app.models.camera_recording import CameraRecording
from app.models.class_session import ClassSession
from app.schemas.ai_monitoring_schema import AIMonitoringEventCreate
from app.services.ai_monitoring_service import create_ai_monitoring_event
from app.services.camera_monitoring_service import camera_service, convert_recording_to_webm

router = APIRouter(tags=["Camera Monitoring"])
templates = Jinja2Templates(directory="app/templates")

BACKEND_ROOT = Path(__file__).resolve().parents[2]
RECORDINGS_DIR = BACKEND_ROOT / "app" / "static" / "recordings"

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

    # Browser playback is official only for our new WebM recordings.
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
def dashboard_start_camera(session_id: Optional[int] = Form(None)):
    camera_service.start(0)
    url = "/dashboard/camera-monitoring"
    if session_id:
        url += f"?session_id={session_id}"
    return RedirectResponse(url=url, status_code=303)


@router.post("/dashboard/camera-monitoring/stop")
def dashboard_stop_camera(session_id: Optional[int] = Form(None)):
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
""")

write_file("app/templates/camera_monitoring/index.html", r"""
{% extends "base.html" %}

{% block title %}Camera Monitoring{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <p class="eyebrow">Phase 9.4 Product Camera Monitoring</p>
        <h1>Camera Monitoring & Video Recording</h1>
        <p>Live camera stream with OpenCV frame boxes, behavior overlays, and browser-compatible WebM recording.</p>
    </div>
    <a class="btn btn-secondary" href="/dashboard/final-demo">Back Final Demo</a>
</div>

<div class="product-note">
    <strong>Product Goal:</strong>
    New recordings use WebM so teachers can watch videos inside the system and download them when needed.
</div>

<div class="card">
    <h2>Session Selection</h2>

    <form method="get" action="/dashboard/camera-monitoring" class="ai-filter-grid">
        <div>
            <label>Session</label>
            <select name="session_id" class="form-control">
                {% for session in sessions %}
                <option value="{{ session.id }}" {% if selected_session and selected_session.id == session.id %}selected{% endif %}>
                    #{{ session.id }} - {{ session.title }}
                    {% if session.active %}(Active){% else %}(Closed){% endif %}
                </option>
                {% endfor %}
            </select>
        </div>

        <div class="ai-filter-actions">
            <button class="btn btn-primary" type="submit">Use Session</button>
        </div>
    </form>

    {% if selected_session %}
    <p class="muted">Selected session: <strong>#{{ selected_session.id }} - {{ selected_session.title }}</strong></p>
    {% endif %}
</div>

<div class="camera-layout">
    <div class="card camera-card">
        <h2>Live Camera</h2>

        <div class="camera-frame-wrap">
            <img class="camera-stream" src="/api/camera-monitoring/stream" alt="Live Camera Stream">
        </div>

        <div class="camera-status-row">
            <span class="camera-status-pill">Camera: {{ "Running" if camera_status.running else "Stopped" }}</span>
            <span class="camera-status-pill">Recording: {{ "Recording" if camera_status.recording else "Not recording" }}</span>
            <span class="camera-status-pill">Format: WebM / VP8</span>
        </div>

        <div class="quick-ai-grid">
            <form method="post" action="/dashboard/camera-monitoring/start">
                <input type="hidden" name="session_id" value="{{ selected_session.id if selected_session else '' }}">
                <button class="btn btn-primary" type="submit">Start Camera</button>
            </form>

            <form method="post" action="/dashboard/camera-monitoring/stop">
                <input type="hidden" name="session_id" value="{{ selected_session.id if selected_session else '' }}">
                <button class="btn btn-danger" type="submit">Stop Camera</button>
            </form>

            <form method="post" action="/dashboard/camera-monitoring/record/start">
                <input type="hidden" name="session_id" value="{{ selected_session.id if selected_session else '' }}">
                <button class="btn btn-warning" type="submit">Start Recording</button>
            </form>

            <form method="post" action="/dashboard/camera-monitoring/record/stop">
                <input type="hidden" name="session_id" value="{{ selected_session.id if selected_session else '' }}">
                <button class="btn btn-secondary" type="submit">Stop Recording</button>
            </form>
        </div>
    </div>

    <div class="card">
        <h2>Behavior Marking</h2>
        <p class="muted">These behavior labels appear as overlays on the live stream and recorded video.</p>

        <div class="behavior-grid">
            {% for item in behavior_types %}
            <form method="post" action="/dashboard/camera-monitoring/behavior">
                <input type="hidden" name="session_id" value="{{ selected_session.id if selected_session else '' }}">
                <input type="hidden" name="event_type" value="{{ item }}">
                <input type="hidden" name="severity" value="{{ 'high' if item in ['sleeping', 'attention_low'] else 'medium' }}">
                <button class="btn btn-primary" type="submit">{{ item }}</button>
            </form>
            {% endfor %}
        </div>

        <h3>Recent Behavior Events</h3>
        <div class="mini-event-list">
            {% for event in ai_events %}
            <div class="mini-event">
                <strong>{{ event.event_type }}</strong>
                <span>{{ event.severity }}</span>
                <small>{{ event.created_at.strftime("%H:%M:%S") if event.created_at else "-" }}</small>
            </div>
            {% else %}
            <p class="muted">No behavior events yet.</p>
            {% endfor %}
        </div>
    </div>
</div>

<div class="card">
    <h2>Recording History</h2>

    <div class="table-responsive">
        <table class="data-table">
            <thead>
                <tr>
                    <th>File</th>
                    <th>Session</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Stopped</th>
                    <th>Duration</th>
                    <th>Size</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for item in recordings %}
                <tr>
                    <td>{{ item.filename }}</td>
                    <td>{{ item.session_id or "-" }}</td>
                    <td><span class="camera-status-pill">{{ item.status }}</span></td>
                    <td>{{ item.started_at.strftime("%Y-%m-%d %H:%M:%S") if item.started_at else "-" }}</td>
                    <td>{{ item.stopped_at.strftime("%Y-%m-%d %H:%M:%S") if item.stopped_at else "-" }}</td>
                    <td>{{ "%.1f"|format(item.duration_seconds) if item.duration_seconds is not none else "-" }}s</td>
                    <td>
                        {% if item.file_exists %}
                            {% if item.is_playable %}
                                <span class="file-size-good">{{ item.file_size_mb }} MB</span>
                            {% elif item.is_convertible %}
                                <span class="file-size-warning">{{ item.file_size_mb }} MB legacy MP4</span>
                            {% else %}
                                <span class="file-size-bad">{{ item.file_size_bytes }} bytes</span>
                            {% endif %}
                        {% else %}
                            <span class="file-size-bad">missing</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if item.status == "saved" and item.is_playable %}
                        <div class="recording-action-links">
                            <a class="btn btn-primary btn-sm" href="/dashboard/camera-monitoring/recordings/{{ item.id }}">Watch in System</a>
                            <a class="btn btn-secondary btn-sm" href="/dashboard/camera-monitoring/recordings/{{ item.id }}/download">Download</a>
                        </div>
                        {% elif item.status == "saved" and item.is_convertible %}
                        <div class="recording-action-links">
                            <form method="post" action="/dashboard/camera-monitoring/recordings/{{ item.id }}/convert-webm">
                                <button class="btn btn-warning btn-sm" type="submit">Convert to WebM</button>
                            </form>
                            <a class="btn btn-secondary btn-sm" href="/dashboard/camera-monitoring/recordings/{{ item.id }}/download">Download</a>
                        </div>
                        {% elif item.status == "saved" %}
                            <span class="file-size-bad">Broken / too small</span>
                        {% else %}
                            <span class="muted">Recording...</span>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="8" class="muted">No recordings yet.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<div class="card">
    <h2>Important Product Note</h2>
    <p class="muted">
        New recordings use WebM/VP8 for in-system playback. Old MP4 files may be legacy recordings and can be converted to WebM when possible.
    </p>
</div>
{% endblock %}
""")

write_file("app/templates/camera_monitoring/playback.html", r"""
{% extends "base.html" %}

{% block title %}Recording Playback{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <p class="eyebrow">Phase 9.4 Recording Playback</p>
        <h1>Recording Playback</h1>
        <p>Watch the saved classroom monitoring video inside the system.</p>
    </div>
    <a class="btn btn-secondary" href="/dashboard/camera-monitoring">Back Camera Monitoring</a>
</div>

{% if recording %}
<div class="product-note">
    <strong>Product Feature:</strong>
    Teachers can watch browser-compatible WebM recordings inside the system and download the video file if needed.
</div>

<div class="card">
    <h2>{{ recording.filename }}</h2>

    {% if recording.is_playable %}
    <div class="recording-player-wrap">
        <video class="recording-player" controls preload="metadata">
            <source src="{{ recording.file_path }}" type="{{ recording.media_type }}">
            Your browser does not support video playback.
        </video>
    </div>
    {% elif recording.is_convertible %}
    <div class="broken-recording-warning">
        <strong>This is a legacy MP4 recording.</strong>
        <p>
            File size: {{ recording.file_size_mb }} MB.
            It may not play inside Chrome/Edge because OpenCV MP4 codec may not be browser-compatible.
            Convert it to WebM for in-system playback.
        </p>
        <form method="post" action="/dashboard/camera-monitoring/recordings/{{ recording.id }}/convert-webm">
            <button class="btn btn-warning" type="submit">Convert to WebM</button>
        </form>
    </div>
    {% else %}
    <div class="broken-recording-warning">
        <strong>This recording file is too small or missing.</strong>
        <p>
            File size: {{ recording.file_size_bytes }} bytes.
            Please record a new video.
        </p>
    </div>
    {% endif %}

    <div class="recording-meta-grid">
        <div>
            <span class="muted">Session</span>
            <strong>{{ recording.session_id or "-" }}</strong>
        </div>
        <div>
            <span class="muted">Status</span>
            <strong>{{ recording.status }}</strong>
        </div>
        <div>
            <span class="muted">Started</span>
            <strong>{{ recording.started_at.strftime("%Y-%m-%d %H:%M:%S") if recording.started_at else "-" }}</strong>
        </div>
        <div>
            <span class="muted">Stopped</span>
            <strong>{{ recording.stopped_at.strftime("%Y-%m-%d %H:%M:%S") if recording.stopped_at else "-" }}</strong>
        </div>
        <div>
            <span class="muted">Duration</span>
            <strong>{{ "%.1f"|format(recording.duration_seconds) if recording.duration_seconds is not none else "-" }}s</strong>
        </div>
        <div>
            <span class="muted">File Size</span>
            <strong>{{ recording.file_size_mb }} MB</strong>
        </div>
    </div>

    <div class="quick-ai-grid">
        {% if recording.is_playable %}
        <a class="btn btn-primary" href="{{ recording.file_path }}" target="_blank">Open Raw Video</a>
        {% endif %}
        <a class="btn btn-secondary" href="/dashboard/camera-monitoring/recordings/{{ recording.id }}/download">Download Video</a>
        <a class="btn btn-primary" href="/dashboard/camera-monitoring?session_id={{ recording.session_id }}">Record New Video</a>
    </div>
</div>

<div class="card">
    <h2>What This Video Should Show</h2>
    <ul class="demo-check-list">
        <li>Smart Classroom overlay</li>
        <li>Face frame box</li>
        <li>REC indicator during recording</li>
        <li>Behavior overlay if behavior button was clicked while recording</li>
    </ul>
</div>
{% else %}
<div class="card">
    <h2>Recording not found</h2>
    <p class="muted">The selected recording does not exist.</p>
</div>
{% endif %}
{% endblock %}
""")

# CSS append
css_path = ROOT / "app/static/css/styles.css"
css_text = css_path.read_text(encoding="utf-8")
if "Phase 9.4 Browser Compatible Recording" not in css_text:
    css_text += r"""

/* Phase 9.4 Browser Compatible Recording */
.file-size-warning {
    display: inline-block;
    background: #fffbeb;
    color: #b45309;
    border: 1px solid #fde68a;
    border-radius: 999px;
    padding: 0.25rem 0.6rem;
    font-weight: 700;
}

.recording-action-links form {
    display: inline-block;
}
"""
    css_path.write_text(css_text, encoding="utf-8")
    print("Updated: app/static/css/styles.css")

print("")
print("DONE: Phase 9.4 Browser-Compatible Recording Playback applied.")
