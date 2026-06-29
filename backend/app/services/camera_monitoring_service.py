import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from app.database.database import SessionLocal
from app.models.ai_monitoring_event import AIMonitoringEvent


BACKEND_ROOT = Path(__file__).resolve().parents[2]
RECORDINGS_DIR = BACKEND_ROOT / "app" / "static" / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

FRAME_WIDTH = 960
FRAME_HEIGHT = 540
FRAME_FPS = 20.0

NO_FACE_ATTENTION_SECONDS = 2.5
NO_FACE_LEAVING_SECONDS = 5.0
EYES_MISSING_SLEEPING_SECONDS = 4.0
AUTO_BEHAVIOR_COOLDOWN_SECONDS = 20.0


class CameraMonitoringService:
    def __init__(self):
        self.cap = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.record_lock = threading.Lock()

        self.latest_frame = None
        self.camera_index = 0

        self.recording = False
        self.video_writer = None
        self.recording_path = None
        self.recording_started_at = None

        self.last_behavior = None
        self.last_behavior_time = 0

        self.monitoring_session_id = None
        self.auto_behavior_enabled = False
        self.no_face_started_at = None
        self.eyes_missing_started_at = None
        self.last_logged_behavior_time = {}
        self.auto_behavior_events_memory = []

        face_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        eye_cascade_path = cv2.data.haarcascades + "haarcascade_eye.xml"

        self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
        self.eye_cascade = cv2.CascadeClassifier(eye_cascade_path)

    def set_session(self, session_id: int | None):
        self.monitoring_session_id = session_id

    def enable_auto_behavior(self, session_id: int | None = None):
        self.monitoring_session_id = session_id
        self.auto_behavior_enabled = True
        self.no_face_started_at = None
        self.eyes_missing_started_at = None
        return self.get_status()

    def disable_auto_behavior(self):
        self.auto_behavior_enabled = False
        self.no_face_started_at = None
        self.eyes_missing_started_at = None
        return self.get_status()

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
        self.disable_auto_behavior()
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

            with self.record_lock:
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

        if self.auto_behavior_enabled:
            self._run_behavior_engine(frame, gray, faces)

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

        if self.auto_behavior_enabled:
            cv2.putText(
                frame,
                "AUTO BEHAVIOR: ON",
                (w - 300, 31),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
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
            source = self.last_behavior.get("source", "manual")
            color = (0, 0, 255) if severity == "high" else (0, 165, 255)

            cv2.rectangle(frame, (30, h - 92), (w - 30, h - 25), color, -1)
            cv2.putText(
                frame,
                f"Behavior Event: {label} | Severity: {severity} | {source}",
                (50, h - 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.78,
                (255, 255, 255),
                2,
            )

        return frame

    def _run_behavior_engine(self, frame, gray, faces):
        now = time.time()

        if len(faces) == 0:
            if self.no_face_started_at is None:
                self.no_face_started_at = now

            no_face_seconds = now - self.no_face_started_at

            if no_face_seconds >= NO_FACE_ATTENTION_SECONDS:
                self._log_auto_behavior_event(
                    event_type="attention_low",
                    severity="high",
                    confidence=0.72,
                    description="Auto behavior engine: no face visible for attention threshold.",
                )

            if no_face_seconds >= NO_FACE_LEAVING_SECONDS:
                self._log_auto_behavior_event(
                    event_type="leaving_seat",
                    severity="high",
                    confidence=0.82,
                    description="Auto behavior engine: student may have left seat because face disappeared.",
                )

            self.eyes_missing_started_at = None
            return

        self.no_face_started_at = None

        largest_face = max(faces, key=lambda item: item[2] * item[3])
        x, y, fw, fh = largest_face

        roi_gray = gray[y:y + fh, x:x + fw]
        eyes = self.eye_cascade.detectMultiScale(
            roi_gray,
            scaleFactor=1.15,
            minNeighbors=5,
            minSize=(18, 18),
        )

        if len(eyes) == 0:
            if self.eyes_missing_started_at is None:
                self.eyes_missing_started_at = now

            eyes_missing_seconds = now - self.eyes_missing_started_at

            if eyes_missing_seconds >= EYES_MISSING_SLEEPING_SECONDS:
                self._log_auto_behavior_event(
                    event_type="sleeping",
                    severity="high",
                    confidence=0.74,
                    description="Auto behavior engine: face detected but eyes were not detected for sleeping threshold.",
                )
        else:
            self.eyes_missing_started_at = None

    def _log_auto_behavior_event(self, event_type: str, severity: str, confidence: float, description: str):
        now = time.time()
        last_time = self.last_logged_behavior_time.get(event_type, 0)

        if now - last_time < AUTO_BEHAVIOR_COOLDOWN_SECONDS:
            return

        self.last_logged_behavior_time[event_type] = now

        event_memory = {
            "event_type": event_type,
            "severity": severity,
            "confidence": round(confidence, 2),
            "description": description,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "session_id": self.monitoring_session_id,
        }

        self.auto_behavior_events_memory.insert(0, event_memory)
        self.auto_behavior_events_memory = self.auto_behavior_events_memory[:20]

        self.last_behavior = {
            "event_type": event_type,
            "severity": severity,
            "source": "auto",
        }
        self.last_behavior_time = time.time()

        try:
            db = SessionLocal()
            event = AIMonitoringEvent(
                session_id=self.monitoring_session_id,
                student_id=None,
                event_type=event_type,
                severity=severity,
                confidence=round(confidence, 2),
                source="camera_auto_behavior_engine",
                description=description,
            )
            db.add(event)
            db.commit()
            db.close()
            print(f"AUTO BEHAVIOR LOGGED: {event_type} | {severity}")
        except Exception as exc:
            print(f"Auto behavior DB log failed: {exc}")

    def set_behavior_overlay(self, event_type: str, severity: str = "info"):
        self.last_behavior = {
            "event_type": event_type,
            "severity": severity,
            "source": "manual",
        }
        self.last_behavior_time = time.time()

    def start_recording(self, session_id: int | None = None):
        self.monitoring_session_id = session_id

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
        with self.record_lock:
            if not self.recording and self.video_writer is None:
                return None

            stopped_at = datetime.utcnow()
            started_at = self.recording_started_at
            path = self.recording_path
            filename = path.name if path else None
            writer = self.video_writer

            self.recording = False
            self.video_writer = None
            self.recording_path = None
            self.recording_started_at = None

        duration = None
        if started_at:
            duration = (stopped_at - started_at).total_seconds()

        if writer:
            try:
                writer.release()
            except Exception as exc:
                print(f"VideoWriter release warning: {exc}")

        result = {
            "path": str(path) if path else None,
            "filename": filename,
            "started_at": started_at,
            "stopped_at": stopped_at,
            "duration_seconds": duration,
        }

        if path and path.exists():
            print(f"Recording saved: {path}")
            print(f"Recording size: {path.stat().st_size} bytes")

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
            "auto_behavior_enabled": self.auto_behavior_enabled,
            "monitoring_session_id": self.monitoring_session_id,
            "recent_auto_behavior_events": self.auto_behavior_events_memory,
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
