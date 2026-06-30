import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from app.database.database import SessionLocal
from app.models.ai_monitoring_event import AIMonitoringEvent
from app.models.attendance_record import AttendanceRecord
from app.models.device import Device
from app.services.face_service import FACE_ATTENDANCE_MIN_CONFIDENCE
from app.services.object_detection_service import object_detection_service


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
AUTO_BEHAVIOR_EVENT_COOLDOWN_SECONDS = 15.0
OBJECT_STABLE_SECONDS = 2.5
OBJECT_EVENT_COOLDOWN_SECONDS = 15.0
OBJECT_DETECTION_INTERVAL_SECONDS = 0.4
IOT_AUTO_UPDATE_INTERVAL_SECONDS = 1.0
IOT_EMPTY_AUTO_OFF_SECONDS = 300.0
OCCUPIED_ATTENDANCE_STATUSES = ["P", "L", "Pm"]


class CameraMonitoringService:
    def __init__(self):
        self.cap = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.record_lock = threading.Lock()
        self.state_lock = threading.Lock()

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
        self.auto_face_attendance_enabled = True
        self.object_detection_enabled = False
        self.object_detection_has_started_once = False
        self.object_detection_started_at = {}
        self.last_object_event_time = {}
        self.latest_object_detections = []
        self.last_object_detection_run_at = 0
        self.cached_object_detections = []
        self.latest_person_count = 0
        self.latest_phone_detected = False
        self.latest_book_detected = False
        self.latest_face_count = 0
        self.latest_face_status = "No face detected"
        self.latest_present_count = 0
        self.latest_occupancy_count = 0
        self.latest_light_relay = "unknown"
        self.latest_fan_relay = "unknown"
        self.iot_auto_control_status = "Off"
        self.last_occupancy_seen_at = None
        self.last_iot_auto_update_at = 0
        self.iot_auto_off_remaining_seconds = None
        self.live_state = {}
        self.face_attendance_events_memory = []
        self.face_attendance_marked_keys = set()

        face_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        eye_cascade_path = cv2.data.haarcascades + "haarcascade_eye.xml"

        self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
        self.eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
        self._sync_live_state()

    def set_session(self, session_id: int | None):
        self.monitoring_session_id = session_id
        self._sync_live_state()

    def enable_auto_behavior(self, session_id: int | None = None):
        self.monitoring_session_id = session_id
        self.auto_behavior_enabled = True
        self.no_face_started_at = None
        self.eyes_missing_started_at = None
        self._sync_live_state()
        return self.get_status()

    def disable_auto_behavior(self):
        self.auto_behavior_enabled = False
        self.no_face_started_at = None
        self.eyes_missing_started_at = None
        self._sync_live_state()
        return self.get_status()

    def enable_auto_face_attendance(self, session_id: int | None = None):
        self.monitoring_session_id = session_id
        self.auto_face_attendance_enabled = True
        self._sync_live_state()
        return self.get_status()

    def disable_auto_face_attendance(self):
        self.auto_face_attendance_enabled = False
        self._sync_live_state()
        return self.get_status()

    def enable_object_detection(self, session_id: int | None = None):
        self.monitoring_session_id = session_id
        status = object_detection_service.status()
        self.object_detection_enabled = bool(status.get("enabled"))
        if self.object_detection_enabled:
            self.object_detection_has_started_once = True
        self.object_detection_started_at = {}
        self._sync_live_state()
        return self.get_status()

    def disable_object_detection(self):
        self.object_detection_enabled = False
        self.object_detection_started_at = {}
        self.latest_object_detections = []
        self.cached_object_detections = []
        self.latest_person_count = 0
        self.latest_phone_detected = False
        self.latest_book_detected = False
        self._sync_live_state()
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
        self._sync_live_state()
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.stop_recording()
        self.disable_auto_behavior()
        self.disable_auto_face_attendance()
        self.disable_object_detection()
        self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.5)

        if self.cap:
            self.cap.release()
            self.cap = None

        with self.lock:
            self.latest_frame = None

        self._sync_live_state()
        return True

    def _capture_loop(self):
        while self.running:
            ok, frame = self.cap.read()

            if not ok or frame is None:
                frame = self._blank_frame("Camera frame not available")

            try:
                annotated = self._annotate_frame(frame)
            except Exception as exc:
                print(f"Overlay draw warning: {exc}")
                annotated = frame
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

        self.latest_face_count = len(faces)
        self.latest_face_status = f"{len(faces)} face(s) detected" if len(faces) else "No face detected"
        object_detections = self.cached_object_detections if self.object_detection_enabled else []
        if self.object_detection_enabled:
            object_detections, refreshed = self._get_object_detections(frame)
            if refreshed:
                self._run_object_behavior_engine(object_detections)
        else:
            self._update_detection_summary([])

        self._update_iot_auto_control(len(faces), object_detections)

        timestamp = datetime.now().strftime("%H:%M:%S")
        self._draw_monitoring_header(frame, w, timestamp)

        if len(faces) > 1:
            self._remember_face_attendance_event(
                "multiple_faces",
                f"{len(faces)} faces detected. Attendance requires a confident single-student match.",
                marked=False,
            )

        if len(faces) > 0:
            for idx, (x, y, fw, fh) in enumerate(faces, start=1):
                face_gray = gray[y:y + fh, x:x + fw]
                label, color = self._recognize_face_label(face_gray, idx)

                cv2.rectangle(frame, (x, y), (x + fw, y + fh), color, 2)
                self._draw_label_box(frame, label, x, max(52, y - 22), color)
        else:
            self._remember_face_attendance_event(
                "no_face_detected",
                "No face visible in the camera frame.",
                marked=False,
            )
            self._draw_label_box(frame, "Unknown face", 22, 58, (0, 140, 255))

        self._draw_object_detections(frame, object_detections)

        if self.recording:
            cv2.circle(frame, (w - 145, 24), 10, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (w - 125, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (0, 0, 255), 2)

        if self.last_behavior and time.time() - self.last_behavior_time <= 8:
            label = self.last_behavior.get("event_type", "behavior")
            severity = self.last_behavior.get("severity", "info")
            source = self.last_behavior.get("source", "manual")
            self._draw_behavior_alert(frame, w, h, label, severity, source)

        return frame

    def _draw_monitoring_header(self, frame, width: int, timestamp: str):
        cv2.rectangle(frame, (0, 0), (width, 44), (15, 23, 42), -1)
        cv2.putText(
            frame,
            "Smart Classroom AI Monitoring",
            (16, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        chips = [
            ("FACE ON" if self.auto_face_attendance_enabled else "FACE OFF", (22, 163, 74) if self.auto_face_attendance_enabled else (100, 116, 139)),
            ("YOLO ON" if self.object_detection_enabled else "YOLO OFF", (37, 99, 235) if self.object_detection_enabled else (100, 116, 139)),
            ("BEHAVIOR ON" if self.auto_behavior_enabled else "BEHAVIOR OFF", (245, 158, 11) if self.auto_behavior_enabled else (100, 116, 139)),
            (f"SESSION #{self.monitoring_session_id or '-'}", (71, 85, 105)),
        ]
        x = 316
        for text, rgb in chips:
            (text_w, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
            if x + text_w + 16 > width - 90:
                break
            bgr = (rgb[2], rgb[1], rgb[0])
            x = self._draw_status_chip(frame, text, x, 12, bgr)

        cv2.putText(frame, timestamp, (width - 78, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (203, 213, 225), 1, cv2.LINE_AA)

    def _draw_status_chip(self, frame, text: str, x: int, y: int, color):
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
        pad_x = 8
        chip_w = text_w + pad_x * 2
        cv2.rectangle(frame, (x, y), (x + chip_w, y + 20), color, -1)
        cv2.putText(frame, text, (x + pad_x, y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
        return x + chip_w + 7

    def _draw_label_box(self, frame, text: str, x: int, y: int, color):
        h, w = frame.shape[:2]
        x = max(4, min(x, w - 80))
        y = max(48, min(y, h - 22))
        while len(text) > 8:
            (candidate_w, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            if candidate_w + 12 <= w - x - 4:
                break
            text = text[:-2].rstrip() + "."
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        box_w = min(text_w + 12, w - x - 4)
        cv2.rectangle(frame, (x, y), (x + box_w, y + 20), color, -1)
        cv2.putText(frame, text, (x + 6, y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    def _draw_behavior_alert(self, frame, width: int, height: int, label: str, severity: str, source: str):
        is_high_phone = severity == "high" and label == "phone_usage"
        if severity == "high":
            color = (0, 0, 220)
            text = f"Alert: {label.replace('_', ' ')}"
        else:
            color = (0, 140, 255) if severity == "medium" else (90, 90, 90)
            text = f"Behavior: {label.replace('_', ' ')}"

        if source:
            text = f"{text} | {source}"

        font_scale = 0.48 if not is_high_phone else 0.54
        thickness = 1 if not is_high_phone else 2
        (text_w, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        bar_w = min(width - 32, text_w + 24)
        x1 = 16
        y1 = height - 42
        cv2.rectangle(frame, (x1, y1), (x1 + bar_w, height - 14), color, -1)
        cv2.putText(frame, text, (x1 + 10, height - 23), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    def _draw_object_detections(self, frame, detections):
        for detection in detections:
            if detection.label == "cell phone":
                color = (0, 0, 255)
                label = "PHONE"
            elif detection.label == "book":
                color = (255, 90, 0)
                label = "BOOK"
            else:
                color = (0, 180, 0)
                label = "PERSON"

            cv2.rectangle(frame, (detection.x1, detection.y1), (detection.x2, detection.y2), color, 2)
            self._draw_label_box(frame, f"{label} {detection.confidence:.2f}", detection.x1, max(52, detection.y1 - 22), color)

    def _get_object_detections(self, frame):
        now = time.time()
        if now - self.last_object_detection_run_at < OBJECT_DETECTION_INTERVAL_SECONDS:
            return self.cached_object_detections, False

        detections = object_detection_service.detect(frame)
        self.last_object_detection_run_at = now
        self.cached_object_detections = detections
        self.latest_object_detections = [item.to_dict() for item in detections]
        self._update_detection_summary(detections)
        return detections, True

    def _update_detection_summary(self, detections):
        self.latest_person_count = sum(1 for item in detections if item.label == "person")
        self.latest_phone_detected = any(item.label == "cell phone" for item in detections)
        self.latest_book_detected = any(item.label == "book" for item in detections)
        self._sync_live_state()

    def _run_object_behavior_engine(self, detections):
        now = time.time()
        active_event_types = {detection.event_type for detection in detections if detection.event_type}

        for event_type in ["phone_usage", "book_usage"]:
            if event_type in active_event_types:
                self.object_detection_started_at.setdefault(event_type, now)
                stable_for = now - self.object_detection_started_at[event_type]
                last_logged = self.last_object_event_time.get(event_type, 0)
                if stable_for >= OBJECT_STABLE_SECONDS and now - last_logged >= OBJECT_EVENT_COOLDOWN_SECONDS:
                    severity = "high" if event_type == "phone_usage" else "low"
                    description = f"YOLO object detection observed stable {event_type.replace('_', ' ')} for {stable_for:.1f}s."
                    self.last_object_event_time[event_type] = now
                    self._log_object_behavior_event(event_type, severity, 0.82, description)
            else:
                self.object_detection_started_at.pop(event_type, None)

    def _log_object_behavior_event(self, event_type: str, severity: str, confidence: float, description: str):
        event_memory = {
            "event_type": event_type,
            "severity": severity,
            "confidence": round(confidence, 2),
            "description": description,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "session_id": self.monitoring_session_id,
            "source": "object_detection_yolo",
        }
        self.auto_behavior_events_memory.insert(0, event_memory)
        self.auto_behavior_events_memory = self.auto_behavior_events_memory[:20]
        self.last_behavior = {
            "event_type": event_type,
            "severity": severity,
            "source": "object_detection_yolo",
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
                source="object_detection_yolo",
                description=description,
            )
            db.add(event)
            db.commit()
            db.close()
            print(f"OBJECT BEHAVIOR LOGGED: {event_type} | {severity}")
        except Exception as exc:
            print(f"Object behavior DB log failed: {exc}")

    def _update_iot_auto_control(self, face_count: int, detections):
        now = time.time()
        if now - self.last_iot_auto_update_at < IOT_AUTO_UPDATE_INTERVAL_SECONDS:
            return

        self.last_iot_auto_update_at = now
        person_count = self.latest_person_count
        present_count = 0
        db = None

        try:
            db = SessionLocal()
            if self.monitoring_session_id:
                present_count = (
                    db.query(AttendanceRecord)
                    .filter(AttendanceRecord.session_id == self.monitoring_session_id)
                    .filter(AttendanceRecord.status.in_(OCCUPIED_ATTENDANCE_STATUSES))
                    .count()
                )

            occupancy_count = max(person_count, face_count, present_count)
            self.latest_person_count = person_count
            self.latest_face_count = face_count
            self.latest_present_count = present_count
            self.latest_occupancy_count = occupancy_count

            if occupancy_count > 0:
                self.last_occupancy_seen_at = datetime.utcnow()
                self.iot_auto_control_status = "Active"
                self.iot_auto_off_remaining_seconds = None
                self._set_simulated_relay_status(db, "on")
            else:
                if self.last_occupancy_seen_at is None:
                    self.iot_auto_control_status = "Waiting"
                    self.iot_auto_off_remaining_seconds = None
                    self._set_simulated_relay_status(db, "off")
                else:
                    empty_for = (datetime.utcnow() - self.last_occupancy_seen_at).total_seconds()
                    remaining = max(0, int(IOT_EMPTY_AUTO_OFF_SECONDS - empty_for))
                    self.iot_auto_off_remaining_seconds = remaining
                    if remaining <= 0:
                        self.iot_auto_control_status = "Auto Off"
                        self._set_simulated_relay_status(db, "off")
                    else:
                        self.iot_auto_control_status = "Countdown"

            self._refresh_relay_status(db)
            self._sync_live_state()
        except Exception as exc:
            self.iot_auto_control_status = "Waiting"
            self._sync_live_state()
            print(f"IoT auto-control update failed: {exc}")
        finally:
            if db:
                db.close()

    def _set_simulated_relay_status(self, db, status: str):
        changed = False
        devices = db.query(Device).filter(Device.type.in_(["light", "fan"])).all()
        for device in devices:
            if device.status != status:
                device.status = status
                device.last_seen = datetime.utcnow()
                changed = True
        if changed:
            db.commit()

    def _refresh_relay_status(self, db):
        relays = {item.type: item.status for item in db.query(Device).filter(Device.type.in_(["light", "fan"])).all()}
        self.latest_light_relay = relays.get("light", "unknown")
        self.latest_fan_relay = relays.get("fan", "unknown")

    def _remember_face_attendance_event(self, event_type: str, message: str, marked: bool, student_id: int | None = None):
        now = time.time()
        dedupe_key = f"{event_type}:{message}:{student_id or ''}"
        last_key = getattr(self, "_last_face_memory_key", None)
        last_time = getattr(self, "_last_face_memory_time", 0)

        if dedupe_key == last_key and now - last_time < 4:
            return

        self._last_face_memory_key = dedupe_key
        self._last_face_memory_time = now
        self.face_attendance_events_memory.insert(
            0,
            {
                "event_type": event_type,
                "message": message,
                "marked": marked,
                "student_id": student_id,
                "session_id": self.monitoring_session_id,
                "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        self.face_attendance_events_memory = self.face_attendance_events_memory[:20]

    def _recognize_face_label(self, face_gray, index: int):
        try:
            from app.models.student import Student
            from app.services.face_product_service import live_face_recognizer
            from app.services.face_service import simulate_face_attendance
        except Exception:
            return f"Face #{index} | recognition unavailable", (0, 0, 255)

        prediction = live_face_recognizer.predict_face(face_gray)

        if not prediction:
            self._remember_face_attendance_event(
                "unknown_face",
                "Unknown face detected. Face model is missing, labels are missing, or the face did not match a trained student.",
                marked=False,
            )
            return "Unknown face", (0, 140, 255)

        confidence = float(prediction.get("confidence") or 0)
        stu_id = prediction.get("stu_id")

        db = SessionLocal()
        try:
            student = db.query(Student).filter(Student.stu_id == stu_id).first()
            name = student.name if student else "Unknown Student"

            if confidence < FACE_ATTENDANCE_MIN_CONFIDENCE:
                self._remember_face_attendance_event(
                    "low_confidence",
                    f"Low confidence match ({confidence:.2f}); attendance not marked.",
                    marked=False,
                    student_id=student.id if student else None,
                )
                if stu_id:
                    return f"Possible {stu_id} / low confidence {confidence:.2f}", (0, 140, 255)
                return f"Unknown / low confidence {confidence:.2f}", (0, 140, 255)

            attendance_text = "FACE ready"
            session_key = f"{self.monitoring_session_id}:{student.id if student else stu_id}"

            if self.auto_face_attendance_enabled and student and self.monitoring_session_id:
                if session_key in self.face_attendance_marked_keys:
                    attendance_text = "already marked"
                else:
                    result = simulate_face_attendance(
                        db=db,
                        student_id=student.id,
                        session_id=self.monitoring_session_id,
                        confidence=confidence,
                        raw_source="monitoring_workspace_face_recognition",
                    )
                    attendance_text = result["result"]
                    if result.get("ok"):
                        self.face_attendance_marked_keys.add(session_key)
                    self._remember_face_attendance_event(
                        "face_attendance",
                        f"{stu_id} - {name} marked {result.get('status')} by FACE.",
                        marked=bool(result.get("ok")),
                        student_id=student.id,
                    )
            elif not self.auto_face_attendance_enabled:
                attendance_text = "auto attendance off"
            elif not self.monitoring_session_id:
                attendance_text = "no session"

            return f"{stu_id} - {name}", (0, 180, 0)
        except Exception as exc:
            self._remember_face_attendance_event(
                "face_attendance_error",
                f"Face attendance could not be processed: {exc}",
                marked=False,
            )
            return "Unknown face", (0, 140, 255)
        finally:
            db.close()

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
        cooldown_key = f"{self.monitoring_session_id or 'none'}:{event_type}"
        last_time = self.last_logged_behavior_time.get(cooldown_key, 0)

        if now - last_time < AUTO_BEHAVIOR_EVENT_COOLDOWN_SECONDS:
            return

        self.last_logged_behavior_time[cooldown_key] = now

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
        self._sync_live_state()

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
        self._sync_live_state()

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
            self._sync_live_state()

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
        self._sync_live_state()
        with self.state_lock:
            return dict(self.live_state)

    def _sync_live_state(self):
        object_status = object_detection_service.status()
        with self.state_lock:
            self.live_state = {
            "running": self.running,
            "camera_running": self.running,
            "recording": self.recording,
            "recording_status": "Recording" if self.recording else "Idle",
            "camera_index": self.camera_index,
            "recording_path": str(self.recording_path) if self.recording_path else None,
            "frame_width": FRAME_WIDTH,
            "frame_height": FRAME_HEIGHT,
            "format": "webm_vp8",
            "auto_behavior_enabled": self.auto_behavior_enabled,
            "behavior_detection_running": self.auto_behavior_enabled,
            "auto_face_attendance_enabled": self.auto_face_attendance_enabled,
            "face_attendance_enabled": self.auto_face_attendance_enabled,
            "object_detection_enabled": self.object_detection_enabled,
            "object_detection_has_started_once": self.object_detection_has_started_once,
            "object_detection_running": bool(self.running and self.object_detection_enabled and object_status.get("enabled")),
            "object_detection_status": object_status,
            "latest_object_detections": self.latest_object_detections,
            "object_detection_interval_seconds": OBJECT_DETECTION_INTERVAL_SECONDS,
            "person_count": self.latest_person_count,
            "phone_detected": self.latest_phone_detected,
            "book_detected": self.latest_book_detected,
            "face_count": self.latest_face_count,
            "latest_face_status": self.latest_face_status,
            "present_count": self.latest_present_count,
            "occupancy_count": self.latest_occupancy_count,
            "light_relay": self.latest_light_relay,
            "fan_relay": self.latest_fan_relay,
            "iot_auto_control_status": self.iot_auto_control_status,
            "last_occupancy_seen": self.last_occupancy_seen_at.isoformat() if self.last_occupancy_seen_at else None,
            "iot_auto_off_remaining_seconds": self.iot_auto_off_remaining_seconds,
            "auto_off_countdown_seconds": self.iot_auto_off_remaining_seconds,
            "face_recognition_accept_threshold": FACE_ATTENDANCE_MIN_CONFIDENCE,
            "monitoring_session_id": self.monitoring_session_id,
            "session_id": self.monitoring_session_id,
            "recent_auto_behavior_events": self.auto_behavior_events_memory,
            "recent_face_attendance_events": self.face_attendance_events_memory,
            "updated_at": datetime.utcnow().isoformat(),
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
