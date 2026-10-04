from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.timezone import format_cambodia_datetime
from app.models.attendance_record import AttendanceRecord
from app.models.class_session import ClassSession
from app.models.edge_inference_event import EdgeInferenceEvent
from app.models.student import Student
from app.services.edge_device_service import list_edge_devices


RECENT_EDGE_EVENT_LIMIT = 12


def _json_list(raw: str | None) -> list[dict[str, Any]]:
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def serialize_edge_event(event: EdgeInferenceEvent, names: dict[str, str]) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "device_id": event.device_id,
        "captured_at": format_cambodia_datetime(event.captured_at),
        "face_status": event.face_status,
        "stu_id": event.stu_id,
        "student_name": names.get(event.stu_id or ""),
        "confidence": event.confidence,
        "attendance_result": event.attendance_result,
        "processing_status": event.processing_status,
        "behaviors": [
            str(item.get("event_type"))
            for item in _json_list(event.behavior_events_json)
            if item.get("event_type")
        ],
        "objects": sorted(
            {
                str(item.get("class_name"))
                for item in _json_list(event.object_detections_json)
                if item.get("class_name")
            }
        ),
    }


def recent_edge_events(db: Session, session_id: int, limit: int = RECENT_EDGE_EVENT_LIMIT) -> list[dict[str, Any]]:
    events = (
        db.query(EdgeInferenceEvent)
        .filter(EdgeInferenceEvent.session_id == session_id)
        .order_by(EdgeInferenceEvent.captured_at.desc(), EdgeInferenceEvent.id.desc())
        .limit(limit)
        .all()
    )
    stu_ids = {event.stu_id for event in events if event.stu_id}
    names = (
        {student.stu_id: student.name for student in db.query(Student).filter(Student.stu_id.in_(stu_ids))}
        if stu_ids
        else {}
    )
    return [serialize_edge_event(event, names) for event in events]


def session_attendance_summary(db: Session, session_id: int) -> dict[str, int]:
    records = db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session_id).all()
    summary = {"total": len(records), "present": 0, "late": 0, "absent": 0, "permission": 0, "face": 0, "qr": 0}
    status_keys = {"P": "present", "L": "late", "A": "absent", "Pm": "permission"}

    for record in records:
        key = status_keys.get(record.status)
        if key:
            summary[key] += 1
        method = (record.method or "").upper()
        if method == "FACE":
            summary["face"] += 1
        elif method == "QR":
            summary["qr"] += 1

    return summary


def edge_workspace_summary(db: Session, session: ClassSession | None) -> dict[str, Any]:
    return {
        "devices": list_edge_devices(db),
        "session_id": session.id if session else None,
        "session_active": bool(session.active) if session else False,
        "events": recent_edge_events(db, session.id) if session else [],
        "attendance": session_attendance_summary(db, session.id) if session else None,
    }
