from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import cv2

from app.services.face_product_service import (
    LABELS_PATH,
    MODEL_PATH,
    get_face_detector,
    live_face_recognizer,
)
from app.services.object_detection_service import (
    MODEL_PATH as OBJECT_MODEL_PATH,
)
from app.services.object_detection_service import (
    object_detection_service,
)
from edge_agent.api_client import (
    EdgeAPIClient,
    EdgeAPIError,
)
from edge_agent.config import EdgeAgentConfig
from edge_agent.spool import EventSpool


AGENT_VERSION = "1.0.0-edge-mvp"


def _iso_now() -> str:
    return datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    ).isoformat()


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def _trained_identity_count() -> int:
    if not LABELS_PATH.exists():
        return 0

    try:
        data = json.loads(
            LABELS_PATH.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return 0

    labels = data.get("labels", {})
    return len(labels) if isinstance(labels, dict) else 0


def _bbox(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> dict[str, int]:
    return {
        "x": max(0, int(x1)),
        "y": max(0, int(y1)),
        "width": max(1, int(x2 - x1)),
        "height": max(1, int(y2 - y1)),
    }


class EdgeAgent:
    def __init__(
        self,
        config: EdgeAgentConfig,
    ):
        self.config = config
        self.client = EdgeAPIClient(
            config.api_url,
            config.device_key,
            config.api_timeout_seconds,
        )
        self.spool = EventSpool(
            config.state_dir,
        )
        self.face_detector = None
        self.active_session: dict[str, Any] | None = None
        self.enrolled_ids: set[str] = set()
        self.stable_counts: dict[str, int] = defaultdict(int)
        self.attendance_sent: set[str] = set()
        self.cooldowns: dict[str, float] = {}
        self.last_context_at = 0.0
        self.last_heartbeat_at = 0.0
        self.last_detections = []
        self.unknown_streak = 0
        self.face_model_sha256 = None
        self.object_model_sha256 = None

    def load_models(self) -> None:
        self.face_detector = get_face_detector()

        if (
            self.face_detector is None
            or self.face_detector.empty()
        ):
            raise RuntimeError(
                "OpenCV Haar face detector failed to load."
            )

        live_face_recognizer.load_if_needed()

        if live_face_recognizer.recognizer is None:
            raise RuntimeError(
                "LBPH face model or labels could not be loaded."
            )

        if not object_detection_service.ensure_loaded():
            raise RuntimeError(
                "YOLO ONNX model could not be loaded: "
                f"{object_detection_service.last_error}"
            )

        self.face_model_sha256 = _sha256(MODEL_PATH)
        self.object_model_sha256 = _sha256(
            OBJECT_MODEL_PATH
        )

    def heartbeat_payload(
        self,
        camera_ready: bool,
    ) -> dict[str, Any]:
        return {
            "device_id": self.config.device_id,
            "agent_version": AGENT_VERSION,
            "local_timestamp": _iso_now(),
            "camera_ready": camera_ready,
            "face_model_ready": (
                live_face_recognizer.recognizer
                is not None
            ),
            "object_model_ready": (
                object_detection_service.loaded
            ),
            "ai_pipeline_ready": (
                camera_ready
                and live_face_recognizer.recognizer
                is not None
                and object_detection_service.loaded
            ),
            "trained_identity_count": (
                _trained_identity_count()
            ),
            "face_model_sha256": (
                self.face_model_sha256
            ),
            "object_model_sha256": (
                self.object_model_sha256
            ),
        }

    def refresh_context(self) -> None:
        context = self.client.context()
        active = context.get("active_session")

        previous_session_id = (
            self.active_session.get("session_id")
            if self.active_session
            else None
        )

        if not isinstance(active, dict):
            self.active_session = None
            self.enrolled_ids = set()
            self.stable_counts.clear()
            self.unknown_streak = 0
            return

        self.active_session = active
        students = active.get("students", [])
        self.enrolled_ids = {
            str(item.get("stu_id"))
            for item in students
            if isinstance(item, dict)
            and item.get("stu_id")
        }

        current_session_id = active.get(
            "session_id"
        )

        if current_session_id != previous_session_id:
            self.attendance_sent.clear()
            self.cooldowns.clear()
            self.stable_counts.clear()
            self.unknown_streak = 0

    def flush_spool(self) -> None:
        pending = self.spool.load()
        if not pending:
            return

        remaining = []

        for payload in pending:
            try:
                response = self.client.inference_event(
                    payload
                )

                if (
                    payload.get("face_status")
                    == "recognized"
                    and payload.get(
                        "attendance_requested",
                        True,
                    )
                    and response.get(
                        "attendance_result"
                    ) in {"success", "duplicate"}
                    and self.active_session
                    and int(payload.get("session_id"))
                    == int(
                        self.active_session["session_id"]
                    )
                ):
                    self.attendance_sent.add(
                        str(payload.get("stu_id"))
                    )

            except EdgeAPIError as exc:
                if exc.retryable:
                    remaining.append(payload)
                else:
                    print(
                        "Dropped permanently rejected "
                        f"queued inference: {exc}"
                    )

        self.spool.save(remaining)

    def send_or_queue(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            response = self.client.inference_event(
                payload
            )
            return {
                **response,
                "_edge_delivery": "accepted",
            }

        except EdgeAPIError as exc:
            if not exc.retryable:
                print(
                    "Inference rejected without retry: "
                    f"{exc}"
                )
                return {
                    "_edge_delivery": "rejected",
                }

            added = self.spool.enqueue(payload)
            state = (
                "queued"
                if added
                else "already pending"
            )
            print(
                f"Inference {state} for retry: {exc}"
            )
            return {
                "_edge_delivery": "queued",
                "_queue_added": added,
            }

    def _object_payload(self) -> list[dict[str, Any]]:
        return [
            {
                "class_name": detection.label,
                "confidence": detection.confidence,
                "bbox": _bbox(
                    detection.x1,
                    detection.y1,
                    detection.x2,
                    detection.y2,
                ),
            }
            for detection in self.last_detections
        ]

    def _phone_behavior(
        self,
        stable_recognized: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if len(stable_recognized) != 1:
            return []

        confidences = [
            detection.confidence
            for detection in self.last_detections
            if detection.label == "cell phone"
        ]

        if not confidences:
            return []

        return [
            {
                "event_type": "phone_usage",
                "severity": "medium",
                "confidence": max(confidences),
                "description": (
                    "Cell phone detected by "
                    "the local YOLO Edge pipeline."
                ),
            }
        ]

    def _recognized_payload(
        self,
        session_id: int,
        recognition: dict[str, Any],
        behaviors: list[dict[str, Any]],
        attendance_requested: bool,
    ) -> dict[str, Any]:
        x, y, w, h = recognition["bbox"]

        return {
            "event_id": str(uuid4()),
            "device_id": self.config.device_id,
            "session_id": session_id,
            "captured_at": _iso_now(),
            "face_status": "recognized",
            "stu_id": recognition["stu_id"],
            "confidence": recognition[
                "confidence"
            ],
            "lbph_distance": recognition[
                "distance"
            ],
            "stable_frame_count": recognition[
                "stable_count"
            ],
            "attendance_requested": (
                attendance_requested
            ),
            "face_bbox": {
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
            },
            "object_detections": (
                self._object_payload()
            ),
            "behavior_events": behaviors,
        }

    def _unknown_payload(
        self,
        session_id: int,
        face_box,
    ) -> dict[str, Any]:
        x, y, w, h = face_box

        return {
            "event_id": str(uuid4()),
            "device_id": self.config.device_id,
            "session_id": session_id,
            "captured_at": _iso_now(),
            "face_status": "unknown",
            "stable_frame_count": 0,
            "face_bbox": {
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
            },
            "object_detections": (
                self._object_payload()
            ),
            "behavior_events": [
                {
                    "event_type": "unknown_face",
                    "severity": "info",
                    "description": (
                        "Unrecognized face detected "
                        "by the local Edge pipeline."
                    ),
                }
            ],
        }

    def _cooldown_ready(
        self,
        key: str,
        now: float,
    ) -> bool:
        previous = self.cooldowns.get(
            key,
            0.0,
        )

        if (
            now - previous
            < self.config.event_cooldown_seconds
        ):
            return False

        self.cooldowns[key] = now
        return True

    def process_frame(
        self,
        frame,
        frame_number: int,
    ) -> tuple[list[dict[str, Any]], list]:
        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY,
        )

        faces = self.face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
        )

        if (
            frame_number
            % self.config.object_every_n_frames
            == 0
        ):
            self.last_detections = (
                object_detection_service.detect(
                    frame
                )
            )

        seen_ids = set()
        recognized = []
        unknown_boxes = []

        for face_box in faces:
            x, y, w, h = [
                int(value)
                for value in face_box
            ]
            crop = gray[
                y:y + h,
                x:x + w,
            ]
            prediction = (
                live_face_recognizer.predict_face(
                    crop
                )
            )

            valid = (
                prediction is not None
                and prediction["confidence"]
                >= self.config.face_confidence
                and prediction["stu_id"]
                in self.enrolled_ids
            )

            if not valid:
                prediction_confidence = (
                    float(prediction["confidence"])
                    if prediction is not None
                    else 0.0
                )

                if (
                    prediction is None
                    or prediction_confidence
                    <= self.config.unknown_max_confidence
                ):
                    unknown_boxes.append(
                        (x, y, w, h)
                    )

                continue

            stu_id = prediction["stu_id"]

            if stu_id in seen_ids:
                continue

            seen_ids.add(stu_id)
            self.stable_counts[stu_id] += 1

            recognized.append(
                {
                    "stu_id": stu_id,
                    "confidence": prediction[
                        "confidence"
                    ],
                    "distance": prediction[
                        "distance"
                    ],
                    "bbox": (x, y, w, h),
                    "stable_count": (
                        self.stable_counts[
                            stu_id
                        ]
                    ),
                }
            )

        for stu_id in list(
            self.stable_counts
        ):
            if stu_id not in seen_ids:
                self.stable_counts[stu_id] = 0

        return recognized, unknown_boxes

    def update_unknown_streak(
        self,
        recognized: list[dict[str, Any]],
        unknown_boxes: list,
    ) -> bool:
        if unknown_boxes and not recognized:
            self.unknown_streak += 1
        else:
            self.unknown_streak = 0

        return (
            self.unknown_streak
            >= self.config.unknown_stable_frames
        )

    def annotate(
        self,
        frame,
        recognized: list[dict[str, Any]],
        unknown_boxes: list,
    ) -> None:
        for item in recognized:
            x, y, w, h = item["bbox"]
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2,
            )
            cv2.putText(
                frame,
                (
                    f"{item['stu_id']} "
                    f"{item['confidence']:.2f} "
                    f"[{item['stable_count']}]"
                ),
                (x, max(20, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 0),
                2,
            )

        for x, y, w, h in unknown_boxes:
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 0, 255),
                2,
            )
            cv2.putText(
                frame,
                "Unknown",
                (x, max(20, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 255),
                2,
            )

        for detection in self.last_detections:
            color = (
                (0, 0, 255)
                if detection.label == "cell phone"
                else (255, 160, 0)
            )
            cv2.rectangle(
                frame,
                (
                    detection.x1,
                    detection.y1,
                ),
                (
                    detection.x2,
                    detection.y2,
                ),
                color,
                2,
            )
            cv2.putText(
                frame,
                (
                    f"{detection.label} "
                    f"{detection.confidence:.2f}"
                ),
                (
                    detection.x1,
                    max(20, detection.y1 - 8),
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )

    def run(
        self,
        max_seconds: int | None = None,
    ) -> None:
        self.config.validate_live()
        self.load_models()

        capture = cv2.VideoCapture(
            self.config.camera_index,
            cv2.CAP_DSHOW,
        )

        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(
                self.config.camera_index
            )

        if not capture.isOpened():
            raise RuntimeError(
                f"Camera index "
                f"{self.config.camera_index} "
                "could not be opened."
            )

        started = time.monotonic()
        frame_number = 0

        try:
            self.client.heartbeat(
                self.heartbeat_payload(
                    camera_ready=True
                )
            )
            self.last_heartbeat_at = (
                time.monotonic()
            )
            self.refresh_context()
            self.last_context_at = (
                time.monotonic()
            )
            self.flush_spool()

            print(
                "Real Edge Agent started. "
                "Press Q or ESC to stop."
            )

            while True:
                ok, frame = capture.read()

                if not ok or frame is None:
                    print(
                        "Camera frame read failed."
                    )
                    time.sleep(0.2)
                    continue

                frame_number += 1
                now = time.monotonic()

                if (
                    now - self.last_context_at
                    >= self.config.context_refresh_seconds
                ):
                    try:
                        self.refresh_context()
                        self.flush_spool()
                    except EdgeAPIError as exc:
                        print(
                            f"Context refresh failed: {exc}"
                        )
                    self.last_context_at = now

                if (
                    now - self.last_heartbeat_at
                    >= self.config.heartbeat_seconds
                ):
                    try:
                        self.client.heartbeat(
                            self.heartbeat_payload(
                                camera_ready=True
                            )
                        )
                    except EdgeAPIError as exc:
                        print(
                            f"Heartbeat failed: {exc}"
                        )
                    self.last_heartbeat_at = now

                recognized, unknown_boxes = (
                    self.process_frame(
                        frame,
                        frame_number,
                    )
                )
                unknown_ready = (
                    self.update_unknown_streak(
                        recognized,
                        unknown_boxes,
                    )
                )

                if self.active_session:
                    session_id = int(
                        self.active_session[
                            "session_id"
                        ]
                    )

                    stable = [
                        item
                        for item in recognized
                        if item["stable_count"]
                        >= self.config.stable_frames
                    ]
                    behaviors = self._phone_behavior(
                        stable
                    )

                    for item in stable:
                        stu_id = item["stu_id"]
                        attendance_due = (
                            stu_id
                            not in self.attendance_sent
                        )
                        behavior_due = (
                            bool(behaviors)
                            and self._cooldown_ready(
                                f"phone:{stu_id}",
                                now,
                            )
                        )

                        if not (
                            attendance_due
                            or behavior_due
                        ):
                            continue

                        payload = (
                            self._recognized_payload(
                                session_id,
                                item,
                                (
                                    behaviors
                                    if behavior_due
                                    else []
                                ),
                                attendance_due,
                            )
                        )
                        response = (
                            self.send_or_queue(
                                payload
                            )
                        )

                        delivery = response.get(
                            "_edge_delivery"
                        )

                        if delivery == "queued":
                            if attendance_due:
                                self.attendance_sent.add(
                                    stu_id
                                )
                            continue

                        if delivery == "rejected":
                            continue

                        result = response.get(
                            "attendance_result"
                        )

                        if (
                            attendance_due
                            and result in {
                                "success",
                                "duplicate",
                            }
                        ):
                            self.attendance_sent.add(
                                stu_id
                            )

                        print(
                            "Inference accepted: "
                            f"{stu_id}, "
                            f"attendance={result}, "
                            f"behavior_events="
                            f"{response.get('behavior_event_count')}"
                        )

                    if (
                        unknown_ready
                        and self._cooldown_ready(
                            "unknown_face",
                            now,
                        )
                    ):
                        self.send_or_queue(
                            self._unknown_payload(
                                session_id,
                                max(
                                    unknown_boxes,
                                    key=lambda box: (
                                        box[2] * box[3]
                                    ),
                                ),
                            )
                        )
                        self.unknown_streak = 0

                if self.config.show_window:
                    self.annotate(
                        frame,
                        recognized,
                        unknown_boxes,
                    )
                    cv2.imshow(
                        "Smart Classroom Real Edge AI",
                        frame,
                    )
                    key = cv2.waitKey(1) & 0xFF

                    if key in {
                        ord("q"),
                        27,
                    }:
                        break

                if (
                    max_seconds is not None
                    and now - started
                    >= max_seconds
                ):
                    break

        finally:
            capture.release()
            cv2.destroyAllWindows()

            try:
                self.client.heartbeat(
                    self.heartbeat_payload(
                        camera_ready=False
                    )
                )
            except EdgeAPIError:
                pass


def diagnose(
    config: EdgeAgentConfig,
    camera_test: bool,
) -> int:
    print(f"API URL: {config.api_url}")
    print(f"Device ID: {config.device_id}")
    print(
        "Device Key configured: "
        f"{bool(config.device_key)}"
    )
    print(
        f"LBPH model exists: "
        f"{MODEL_PATH.exists()}"
    )
    print(
        f"Labels exist: "
        f"{LABELS_PATH.exists()}"
    )
    print(
        f"YOLO model exists: "
        f"{OBJECT_MODEL_PATH.exists()}"
    )
    print(
        f"Trained identities: "
        f"{_trained_identity_count()}"
    )

    detector = get_face_detector()
    detector_ready = (
        detector is not None
        and not detector.empty()
    )
    print(
        f"Face detector ready: "
        f"{detector_ready}"
    )

    live_face_recognizer.load_if_needed()
    face_ready = (
        live_face_recognizer.recognizer
        is not None
    )
    print(f"LBPH loaded: {face_ready}")

    object_ready = (
        object_detection_service.ensure_loaded()
    )
    print(f"YOLO loaded: {object_ready}")

    camera_ready = None

    if camera_test:
        capture = cv2.VideoCapture(
            config.camera_index,
            cv2.CAP_DSHOW,
        )

        if not capture.isOpened():
            capture.release()
            capture = cv2.VideoCapture(
                config.camera_index
            )

        ok, frame = capture.read()
        camera_ready = bool(
            capture.isOpened()
            and ok
            and frame is not None
        )
        capture.release()
        print(
            f"Camera frame ready: "
            f"{camera_ready}"
        )

    mandatory = (
        detector_ready
        and face_ready
        and object_ready
        and _trained_identity_count() > 0
    )

    if camera_test:
        mandatory = (
            mandatory
            and bool(camera_ready)
        )

    print(
        "EDGE AGENT DIAGNOSIS: "
        f"{'PASS' if mandatory else 'FAILED'}"
    )

    return 0 if mandatory else 1
