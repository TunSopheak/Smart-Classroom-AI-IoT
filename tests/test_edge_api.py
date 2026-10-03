from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest


def _heartbeat(**overrides):
    payload = {
        "device_id": "test-edge-01",
        "agent_version": "test",
        "local_timestamp": datetime.now(timezone.utc).isoformat(),
        "camera_ready": True,
        "face_model_ready": True,
        "object_model_ready": True,
        "ai_pipeline_ready": True,
        "trained_identity_count": 5,
    }
    payload.update(overrides)
    return payload


def _recognized(session_id, stu_id="S001", **overrides):
    payload = {
        "event_id": str(uuid4()),
        "device_id": "test-edge-01",
        "session_id": session_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "face_status": "recognized",
        "stu_id": stu_id,
        "confidence": 0.82,
        "lbph_distance": 18.0,
        "stable_frame_count": 6,
        "attendance_requested": True,
        "face_bbox": {"x": 10, "y": 10, "width": 120, "height": 120},
    }
    payload.update(overrides)
    return payload


def _post_event(client, headers, payload):
    return client.post("/api/edge/v1/inference-events", json=payload, headers=headers)


def _attendance_events(db, session_id, result=None):
    from app.models.attendance_event import AttendanceEvent

    query = db.query(AttendanceEvent).filter(AttendanceEvent.session_id == session_id)
    if result is not None:
        query = query.filter(AttendanceEvent.result == result)
    return query.all()


def _monitoring_events(db, session_id):
    from app.models.ai_monitoring_event import AIMonitoringEvent

    return db.query(AIMonitoringEvent).filter(AIMonitoringEvent.session_id == session_id).all()


# ---------------------------------------------------------------- auth


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/edge/v1/heartbeat"),
        ("get", "/api/edge/v1/context"),
        ("post", "/api/edge/v1/inference-events"),
    ],
)
def test_edge_endpoints_require_device_key(client, method, path):
    assert getattr(client, method)(path).status_code == 401

    wrong = {"x-smart-classroom-device-key": "wrong-key"}
    assert getattr(client, method)(path, headers=wrong).status_code == 401


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/object-detection/stream"),
        ("get", "/api/monitoring/status"),
        ("post", "/api/monitoring/start"),
        ("post", "/api/monitoring/stop"),
        ("get", "/api/classes"),
    ],
)
def test_camera_and_monitoring_routes_require_login(client, method, path):
    # Regression for PR #20: these used to be reachable without login.
    # 401 is returned by the middleware, so no camera is ever opened.
    assert getattr(client, method)(path).status_code == 401


# ---------------------------------------------------------- heartbeat / context


def test_heartbeat_ready_and_degraded(client, device_headers):
    response = client.post("/api/edge/v1/heartbeat", json=_heartbeat(), headers=device_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

    response = client.post(
        "/api/edge/v1/heartbeat",
        json=_heartbeat(camera_ready=False, ai_pipeline_ready=False),
        headers=device_headers,
    )
    assert response.json()["status"] == "degraded"


def test_context_returns_active_session_and_enrolled_students(client, device_headers, active_session):
    response = client.get("/api/edge/v1/context", headers=device_headers)
    assert response.status_code == 200

    body = response.json()
    assert body["attendance_face_threshold"] == 0.60
    assert body["active_session"]["session_id"] == active_session.id
    stu_ids = {item["stu_id"] for item in body["active_session"]["students"]}
    assert {"S001", "S002", "S003", "S004", "S005"} <= stu_ids


# ------------------------------------------------------------- attendance


def test_recognized_face_marks_attendance_once(client, device_headers, db, active_session):
    response = _post_event(client, device_headers, _recognized(active_session.id))
    assert response.status_code == 200

    body = response.json()
    assert body["attendance_result"] == "success"
    assert body["attendance_recorded"] is True

    from app.models.attendance_record import AttendanceRecord

    record = db.get(AttendanceRecord, body["attendance_record_id"])
    assert record.status == "P"
    assert record.method == "FACE"
    assert len(_attendance_events(db, active_session.id)) == 1


def test_same_event_id_is_idempotent(client, device_headers, db, active_session):
    from app.models.edge_inference_event import EdgeInferenceEvent

    payload = _recognized(active_session.id)
    first = _post_event(client, device_headers, payload).json()
    second = _post_event(client, device_headers, payload).json()

    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["attendance_result"] == first["attendance_result"] == "success"
    assert db.query(EdgeInferenceEvent).filter(EdgeInferenceEvent.event_id == payload["event_id"]).count() == 1
    assert len(_attendance_events(db, active_session.id)) == 1


def test_second_sighting_is_attendance_duplicate(client, device_headers, db, active_session):
    _post_event(client, device_headers, _recognized(active_session.id))
    body = _post_event(client, device_headers, _recognized(active_session.id)).json()

    assert body["attendance_result"] == "duplicate"
    assert len(_attendance_events(db, active_session.id, result="success")) == 1


def test_unstable_face_does_not_mark_attendance(client, device_headers, db, active_session):
    body = _post_event(
        client, device_headers, _recognized(active_session.id, stable_frame_count=3)
    ).json()

    assert body["attendance_result"] == "unstable_face"
    assert _attendance_events(db, active_session.id) == []


def test_after_close_is_logged_but_not_marked(client, device_headers, db, active_session):
    captured = active_session.close_time.replace(tzinfo=timezone.utc) + timedelta(minutes=1)
    body = _post_event(
        client,
        device_headers,
        _recognized(active_session.id, captured_at=captured.isoformat()),
    ).json()

    assert body["attendance_result"] == "after_close"
    assert body["attendance_recorded"] is False


def test_unenrolled_student_is_rejected(client, device_headers, db, active_session):
    from app.models.student import Student

    if not db.query(Student).filter(Student.stu_id == "S900").first():
        db.add(Student(stu_id="S900", name="Not Enrolled", qr_code="TEST-S900", active=True))
        db.commit()

    response = _post_event(client, device_headers, _recognized(active_session.id, stu_id="S900"))
    assert response.status_code == 400


# --------------------------------------------------------- behavior / unknown


def test_behavior_only_event_creates_monitoring_event_without_attendance(
    client, device_headers, db, active_session
):
    payload = _recognized(
        active_session.id,
        attendance_requested=False,
        behavior_events=[{"event_type": "phone_usage", "severity": "medium", "confidence": 0.7}],
        object_detections=[{"class_name": "cell phone", "confidence": 0.7}],
    )
    body = _post_event(client, device_headers, payload).json()

    assert body["attendance_result"] is None
    assert body["behavior_event_count"] == 1
    assert _attendance_events(db, active_session.id) == []

    events = _monitoring_events(db, active_session.id)
    assert [event.event_type for event in events] == ["phone_usage"]
    assert events[0].source == "edge_real_ai:test-edge-01"


def test_unknown_face_creates_event_without_student(client, device_headers, db, active_session):
    payload = {
        "event_id": str(uuid4()),
        "device_id": "test-edge-01",
        "session_id": active_session.id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "face_status": "unknown",
        "behavior_events": [{"event_type": "unknown_face", "severity": "info"}],
    }
    body = _post_event(client, device_headers, payload).json()

    assert body["attendance_result"] is None
    events = _monitoring_events(db, active_session.id)
    assert len(events) == 1
    assert events[0].event_type == "unknown_face"
    assert events[0].student_id is None
    assert _attendance_events(db, active_session.id) == []


# ---------------------------------------------------------------- schema


@pytest.mark.parametrize(
    "overrides",
    [
        {"stu_id": None},
        {"confidence": None},
        {"lbph_distance": None},
        {"face_status": "unknown"},  # stu_id must be omitted for unknown faces
        {"confidence": 1.5},
        {"event_id": "not-a-uuid"},
        {"device_id": "bad device id!"},
    ],
)
def test_invalid_payloads_are_rejected(client, device_headers, active_session, overrides):
    response = _post_event(client, device_headers, _recognized(active_session.id, **overrides))
    assert response.status_code == 422


def test_unknown_session_is_rejected(client, device_headers):
    response = _post_event(client, device_headers, _recognized(999999))
    assert response.status_code == 400
