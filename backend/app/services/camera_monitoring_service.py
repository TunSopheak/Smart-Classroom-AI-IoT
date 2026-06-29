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

            # Important fix:
            # Always resize the final annotated frame before streaming and recording.
            # VideoWriter requires every frame to match exactly the configured size.
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

        filename = f"camera_session_{session_id or 'none'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        path = RECORDINGS_DIR / filename

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.video_writer = cv2.VideoWriter(str(path), fourcc, FRAME_FPS, (FRAME_WIDTH, FRAME_HEIGHT))

        if not self.video_writer or not self.video_writer.isOpened():
            self.video_writer = None
            print("ERROR: Could not open VideoWriter.")
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
