from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import AttendanceEventResult
from app.models.class_session import ClassSession
from app.models.edge_inference_event import EdgeInferenceEvent
from app.models.student import Student
from app.schemas.ai_monitoring_schema import AIMonitoringEventCreate
from app.schemas.edge_schema import EdgeInferenceEventRequest
from app.services.ai_monitoring_service import create_ai_monitoring_event
from app.services.attendance_service import is_student_enrolled
from app.services.face_service import record_face_attendance


MIN_STABLE_FACE_FRAMES = 6


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(microsecond=0)
    return value.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def _payload_dict(payload: EdgeInferenceEventRequest) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    return payload.dict()


def _stored_response(record: EdgeInferenceEvent, duplicate: bool) -> dict[str, Any]:
    if record.response_json:
        response = json.loads(record.response_json)
        response["duplicate"] = duplicate
        return response

    return {
        "success": record.processing_status == "processed",
        "duplicate": duplicate,
        "event_id": record.event_id,
        "processing_status": record.processing_status,
        "face_status": record.face_status,
        "attendance_recorded": False,
        "attendance_result": record.attendance_result,
        "attendance_record_id": record.attendance_record_id,
        "attendance_event_id": record.attendance_event_id,
        "ai_monitoring_event_ids": [],
        "object_detection_count": 0,
        "behavior_event_count": 0,
        "message": record.error_message or "Edge inference event already exists.",
    }


def process_edge_inference_event(
    db: Session,
    payload: EdgeInferenceEventRequest,
) -> dict[str, Any]:
    event_id = str(payload.event_id)

    existing = (
        db.query(EdgeInferenceEvent)
        .filter(EdgeInferenceEvent.event_id == event_id)
        .first()
    )
    if existing is not None:
        return _stored_response(existing, duplicate=True)

    session = db.get(ClassSession, payload.session_id)
    if session is None:
        raise ValueError("Class session not found.")

    student = None
    if payload.face_status == "recognized":
        student = (
            db.query(Student)
            .filter(Student.stu_id == payload.stu_id)
            .first()
        )
        if student is None or not student.active:
            raise ValueError("Recognized student was not found or is inactive.")
        if not is_student_enrolled(db, session, student.id):
            raise ValueError("Recognized student is not enrolled in this session.")

    data = _payload_dict(payload)
    captured_at = _naive_utc(payload.captured_at)

    record = EdgeInferenceEvent(
        event_id=event_id,
        device_id=payload.device_id,
        session_id=payload.session_id,
        captured_at=captured_at,
        face_status=payload.face_status,
        stu_id=payload.stu_id,
        confidence=payload.confidence,
        lbph_distance=payload.lbph_distance,
        stable_frame_count=payload.stable_frame_count,
        face_bbox_json=(
            json.dumps(data.get("face_bbox"), separators=(",", ":"))
            if data.get("face_bbox") is not None
            else None
        ),
        object_detections_json=json.dumps(
            data.get("object_detections", []), separators=(",", ":")
        ),
        behavior_events_json=json.dumps(
            data.get("behavior_events", []), separators=(",", ":")
        ),
        payload_json=json.dumps(data, separators=(",", ":")),
        processing_status="processing",
    )
    db.add(record)

    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(EdgeInferenceEvent)
            .filter(EdgeInferenceEvent.event_id == event_id)
            .first()
        )
        if existing is None:
            raise
        return _stored_response(existing, duplicate=True)

    attendance_result = None
    attendance_record_id = None
    attendance_event_id = None
    attendance_recorded = False
    ai_event_ids: list[int] = []

    try:
        if payload.face_status == "recognized":
            if payload.stable_frame_count < MIN_STABLE_FACE_FRAMES:
                attendance_result = "unstable_face"
            else:
                attendance = record_face_attendance(
                    db=db,
                    student_id=student.id,
                    session_id=session.id,
                    confidence=float(payload.confidence),
                    raw_source=(
                        f"edge:{payload.device_id}:{event_id}"
                    )[:120],
                    event_time=captured_at,
                )
                attendance_result = str(_value(attendance.get("result")))
                attendance_record_id = attendance.get("record_id")
                attendance_event_id = attendance.get("event_id")
                attendance_recorded = attendance_result in {
                    AttendanceEventResult.SUCCESS.value,
                    AttendanceEventResult.DUPLICATE.value,
                }

        source = f"edge_real_ai:{payload.device_id}"[:80]
        for behavior in payload.behavior_events:
            event = create_ai_monitoring_event(
                db,
                AIMonitoringEventCreate(
                    session_id=session.id,
                    student_id=student.id if student is not None else None,
                    event_type=behavior.event_type,
                    severity=behavior.severity,
                    confidence=behavior.confidence,
                    source=source,
                    description=(
                        behavior.description
                        or f"Real Edge AI event {event_id}"
                    ),
                ),
            )
            ai_event_ids.append(event.id)

        response = {
            "success": True,
            "duplicate": False,
            "event_id": event_id,
            "processing_status": "processed",
            "face_status": payload.face_status,
            "attendance_recorded": attendance_recorded,
            "attendance_result": attendance_result,
            "attendance_record_id": attendance_record_id,
            "attendance_event_id": attendance_event_id,
            "ai_monitoring_event_ids": ai_event_ids,
            "object_detection_count": len(payload.object_detections),
            "behavior_event_count": len(payload.behavior_events),
            "message": "Real Edge AI inference event processed.",
        }

        record.processing_status = "processed"
        record.attendance_result = attendance_result
        record.attendance_record_id = attendance_record_id
        record.attendance_event_id = attendance_event_id
        record.response_json = json.dumps(response, separators=(",", ":"))
        record.processed_at = datetime.utcnow()
        record.error_message = None
        db.commit()
        return response

    except Exception as exc:
        db.rollback()
        failed = db.get(EdgeInferenceEvent, record.id)
        if failed is not None:
            failed.processing_status = "failed"
            failed.error_message = str(exc)[:2000]
            failed.processed_at = datetime.utcnow()
            db.commit()
        raise
