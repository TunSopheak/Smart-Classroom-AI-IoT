from pathlib import Path

ROOT = Path(__file__).resolve().parent

def write_file(relative_path: str, content: str):
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Written: {path}")

def read_file(relative_path: str):
    path = ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""

def save_file(relative_path: str, content: str):
    path = ROOT / relative_path
    path.write_text(content, encoding="utf-8")
    print(f"Updated: {path}")

write_file("app/models/camera_recording.py", r"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CameraRecording(Base):
    __tablename__ = "camera_recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("class_sessions.id"), nullable=True, index=True)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="recording", nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    session = relationship("ClassSession")
""")

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

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
        self.cap.set(cv2.CAP_PROP_FPS, 20)

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

            with self.lock:
                self.latest_frame = annotated.copy()

            if self.recording and self.video_writer is not None:
                try:
                    self.video_writer.write(annotated)
                except Exception:
                    pass

            time.sleep(0.03)

    def _blank_frame(self, message: str):
        frame = np.zeros((540, 960, 3), dtype=np.uint8)
        cv2.putText(frame, message, (70, 260), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
        return frame

    def _annotate_frame(self, frame):
        frame = frame.copy()
        h, w = frame.shape[:2]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cv2.rectangle(frame, (0, 0), (w, 46), (15, 23, 42), -1)
        cv2.putText(frame, f"Smart Classroom AI Monitoring | {timestamp}", (18, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)

        if len(faces) > 0:
            for idx, (x, y, fw, fh) in enumerate(faces, start=1):
                cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 3)
                cv2.putText(frame, f"Face #{idx}", (x, max(35, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (0, 255, 0), 2)
        else:
            cv2.rectangle(frame, (30, 65), (390, 115), (0, 0, 255), 2)
            cv2.putText(frame, "No face detected / attention check", (45, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 0, 255), 2)

        if self.recording:
            cv2.circle(frame, (w - 145, 24), 10, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (w - 125, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (0, 0, 255), 2)

        if self.last_behavior and time.time() - self.last_behavior_time <= 8:
            label = self.last_behavior.get("event_type", "behavior")
            severity = self.last_behavior.get("severity", "info")
            color = (0, 0, 255) if severity == "high" else (0, 165, 255)

            cv2.rectangle(frame, (30, h - 92), (w - 30, h - 25), color, -1)
            cv2.putText(frame, f"Behavior Event: {label} | Severity: {severity}", (50, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)

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

        filename = f"camera_session_{session_id or 'none'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        path = RECORDINGS_DIR / filename

        width = 960
        height = 540
        fps = 20.0

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.video_writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))

        if not self.video_writer or not self.video_writer.isOpened():
            self.video_writer = None
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

        self.recording_path = None
        self.recording_started_at = None

        return result

    def get_status(self):
        return {
            "running": self.running,
            "recording": self.recording,
            "camera_index": self.camera_index,
            "recording_path": str(self.recording_path) if self.recording_path else None,
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


camera_service = CameraMonitoringService()
""")

write_file("app/routers/camera_monitoring_router.py", r"""
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
""")

write_file("app/templates/camera_monitoring/index.html", r"""
{% extends "base.html" %}

{% block title %}Camera Monitoring{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <p class="eyebrow">Phase 9 Product Camera Monitoring</p>
        <h1>Camera Monitoring & Video Recording</h1>
        <p>Live camera stream with OpenCV frame boxes, behavior overlays, and recording inside the system.</p>
    </div>
    <a class="btn btn-secondary" href="/dashboard/final-demo">Back Final Demo</a>
</div>

<div class="product-note">
    <strong>Product Goal:</strong>
    This page records real classroom video with AI-style frame boxes and behavior overlays. The recording is saved inside the system for later review.
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
                    <th>Open</th>
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
                        {% if item.status == "saved" %}
                        <a href="{{ item.file_path }}" target="_blank">Open Video</a>
                        {% else %}
                        <span class="muted">Recording...</span>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="7" class="muted">No recordings yet.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<div class="card">
    <h2>Important Product Note</h2>
    <p class="muted">
        Current version records video with face frame boxes and manual behavior overlays.
        Next phase will improve behavior detection logic so the system can detect more behavior automatically.
    </p>
</div>
{% endblock %}
""")

# Update models init
models_init = read_file("app/models/__init__.py")
if "camera_recording" not in models_init:
    models_init += "\nfrom app.models.camera_recording import CameraRecording\n"
    save_file("app/models/__init__.py", models_init)

# Update main.py
main_text = read_file("app/main.py")
if "phase9_camera_monitoring_router" not in main_text:
    main_text += """

# Phase 9 Camera Monitoring routes
from app.routers.camera_monitoring_router import router as phase9_camera_monitoring_router
app.include_router(phase9_camera_monitoring_router)
"""
    save_file("app/main.py", main_text)

# Update base nav
base_text = read_file("app/templates/base.html")
if "/dashboard/camera-monitoring" not in base_text:
    if "/dashboard/ai-monitoring" in base_text:
        base_text = base_text.replace(
            '<a href="/dashboard/ai-monitoring">AI Monitoring</a>',
            '<a href="/dashboard/ai-monitoring">AI Monitoring</a>\n    <a href="/dashboard/camera-monitoring">Camera Monitoring</a>',
            1,
        )
    elif "</nav>" in base_text:
        base_text = base_text.replace(
            "</nav>",
            '    <a href="/dashboard/camera-monitoring">Camera Monitoring</a>\n</nav>',
            1,
        )
    save_file("app/templates/base.html", base_text)

# Update final demo page by adding Camera Monitoring step
demo_router = read_file("app/routers/demo_router.py")
if "Camera Monitoring & Recording" not in demo_router:
    demo_router = demo_router.replace(
        '''{
            "title": "4. AI Monitoring",
            "goal": "Show phone usage, sleeping, leaving seat, hand raising, attention low, and student-level AI events.",
            "url": "/dashboard/ai-monitoring",
        },''',
        '''{
            "title": "4. Camera Monitoring & Recording",
            "goal": "Show live camera, frame boxes, behavior overlays, and video recording inside the system.",
            "url": "/dashboard/camera-monitoring",
        },
        {
            "title": "5. AI Monitoring",
            "goal": "Show phone usage, sleeping, leaving seat, hand raising, attention low, and student-level AI events.",
            "url": "/dashboard/ai-monitoring",
        },''',
    )

    demo_router = demo_router.replace('"5. IoT Monitoring"', '"6. IoT Monitoring"')
    demo_router = demo_router.replace('"6. Reports & Export"', '"7. Reports & Export"')

    if '"Camera monitoring and video recording"' not in demo_router:
        demo_router = demo_router.replace(
            '"Face recognition attendance",',
            '"Face recognition attendance",\n        "Camera monitoring and video recording",',
        )

    save_file("app/routers/demo_router.py", demo_router)

# Gitignore recordings
gitignore = read_file("../.gitignore")
if "backend/app/static/recordings/" not in gitignore:
    gitignore += "\n# Camera recordings privacy\nbackend/app/static/recordings/\n"
    save_file("../.gitignore", gitignore)

# CSS
css_text = read_file("app/static/css/styles.css")
if "Phase 9 Camera Monitoring" not in css_text:
    css_text += r"""

/* Phase 9 Camera Monitoring */
.product-note {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    color: #7c2d12;
    padding: 1rem 1.25rem;
    border-radius: 1rem;
    margin: 1rem 0 1.5rem;
}

.camera-layout {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 1rem;
}

.camera-frame-wrap {
    background: #020617;
    border-radius: 1rem;
    overflow: hidden;
    border: 1px solid #1e293b;
}

.camera-stream {
    display: block;
    width: 100%;
    max-height: 540px;
    object-fit: contain;
    background: #020617;
}

.camera-status-row {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin: 1rem 0;
}

.camera-status-pill {
    display: inline-block;
    background: #eef2ff;
    color: #312e81;
    border: 1px solid #c7d2fe;
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.85rem;
}

.behavior-grid {
    display: grid;
    gap: 0.75rem;
    margin: 1rem 0;
}

.behavior-grid .btn {
    width: 100%;
    text-transform: capitalize;
}

.mini-event-list {
    display: grid;
    gap: 0.5rem;
}

.mini-event {
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    border-bottom: 1px solid #e5e7eb;
    padding: 0.5rem 0;
}

@media (max-width: 1000px) {
    .camera-layout {
        grid-template-columns: 1fr;
    }
}
"""
    save_file("app/static/css/styles.css", css_text)

# Docs
write_file("docs/product_camera_monitoring.md", r"""
# Product Camera Monitoring

## Goal

The product must support classroom video monitoring and recording inside the system.

## Features

- Live camera stream
- OpenCV face frame boxes
- Recording video into the system
- Recorded video includes frame boxes and behavior overlays
- Behavior marking during monitoring
- Recording history

## Behavior Events

Current supported behavior labels:

- phone_usage
- sleeping
- leaving_seat
- attention_low
- hand_raising

## Current Version

This phase records real video with frame boxes and manual behavior overlays.

## Next Version

The next phase will improve automatic behavior detection using CV logic and future YOLO / MediaPipe integration.
""")

print("")
print("DONE: Phase 9 Product Camera Monitoring & Recording applied.")
