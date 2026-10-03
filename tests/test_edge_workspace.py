from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.fixture
def edge_mode(monkeypatch):
    from app.core import monitoring_mode

    monkeypatch.setattr(monitoring_mode, "MONITORING_MODE", monitoring_mode.EDGE_MODE)


def _recognized(session_id, stu_id="S001", **overrides):
    payload = {
        "event_id": str(uuid4()),
        "device_id": "workspace-edge-01",
        "session_id": session_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "face_status": "recognized",
        "stu_id": stu_id,
        "confidence": 0.75,
        "lbph_distance": 25.0,
        "stable_frame_count": 6,
    }
    payload.update(overrides)
    return payload


def test_edge_mode_renders_edge_workspace(edge_mode, teacher_client, active_session):
    response = teacher_client.get(f"/dashboard/monitoring-workspace?session_id={active_session.id}")

    assert response.status_code == 200
    assert "Classroom Edge Agent" in response.text
    assert "edge_agent.main --run" in response.text
    # No server-camera stream or start controls on Render.
    assert "/api/camera-monitoring/stream" not in response.text
    assert "/dashboard/monitoring-workspace/start" not in response.text
    assert "Recording Panel" not in response.text


def test_server_camera_mode_keeps_legacy_workspace(teacher_client, active_session):
    response = teacher_client.get(f"/dashboard/monitoring-workspace?session_id={active_session.id}")

    assert response.status_code == 200
    assert "Live Classroom Camera" in response.text
    assert "Classroom Edge Agent" not in response.text


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/monitoring/start"),
        ("get", "/api/camera-monitoring/stream"),
        ("post", "/dashboard/monitoring-workspace/start"),
        ("post", "/dashboard/camera-monitoring/start"),
        ("post", "/dashboard/camera-monitoring/face-attendance/start"),
        ("post", "/dashboard/camera-monitoring/behavior-auto/start"),
        ("post", "/dashboard/camera-monitoring/record/start"),
    ],
)
def test_edge_mode_blocks_server_camera(edge_mode, teacher_client, method, path):
    # Only exercised in edge mode: in server_camera mode these would open the real webcam.
    response = getattr(teacher_client, method)(path, follow_redirects=False)
    assert response.status_code == 409


def test_session_summary_shows_edge_results(client, device_headers, teacher_client, active_session):
    teacher_client.post(
        "/api/edge/v1/inference-events",
        json=_recognized(active_session.id, object_detections=[{"class_name": "cell phone", "confidence": 0.6}]),
        headers=device_headers,
    )
    teacher_client.post(
        "/api/edge/v1/inference-events",
        json={
            "event_id": str(uuid4()),
            "device_id": "workspace-edge-01",
            "session_id": active_session.id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "face_status": "unknown",
            "behavior_events": [{"event_type": "unknown_face"}],
        },
        headers=device_headers,
    )

    body = teacher_client.get(f"/api/edge-monitoring/sessions/{active_session.id}/summary").json()

    assert body["attendance"]["present"] == 1
    assert body["attendance"]["face"] == 1
    assert [event["face_status"] for event in body["events"]] == ["unknown", "recognized"]

    recognized = body["events"][1]
    assert recognized["stu_id"] == "S001"
    assert recognized["student_name"] == "Tun Sopheak"
    assert recognized["attendance_result"] == "success"
    assert recognized["objects"] == ["cell phone"]
    assert body["events"][0]["behaviors"] == ["unknown_face"]


def test_session_summary_requires_login_and_valid_session(client, teacher_client, active_session):
    assert teacher_client.get("/api/edge-monitoring/sessions/999999/summary").status_code == 404

    teacher_client.post("/logout")
    teacher_client.cookies.clear()
    assert client.get(f"/api/edge-monitoring/sessions/{active_session.id}/summary").status_code == 401
