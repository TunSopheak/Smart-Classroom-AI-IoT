from datetime import datetime, timedelta, timezone

import pytest


def _heartbeat(device_id, **overrides):
    payload = {
        "device_id": device_id,
        "agent_version": "1.0.0-test",
        "local_timestamp": datetime.now(timezone.utc).isoformat(),
        "camera_ready": True,
        "face_model_ready": True,
        "object_model_ready": True,
        "ai_pipeline_ready": True,
        "trained_identity_count": 8,
        "face_model_sha256": "a" * 64,
    }
    payload.update(overrides)
    return payload


def _device(client, device_id):
    devices = client.get("/api/edge-monitoring/devices").json()["devices"]
    return next(item for item in devices if item["device_id"] == device_id)


def test_heartbeat_is_stored_and_updated(client, device_headers, db):
    from app.models.edge_device import EdgeDevice

    client.post("/api/edge/v1/heartbeat", json=_heartbeat("hb-store"), headers=device_headers)
    client.post(
        "/api/edge/v1/heartbeat",
        json=_heartbeat("hb-store", agent_version="1.0.1", trained_identity_count=9),
        headers=device_headers,
    )

    rows = db.query(EdgeDevice).filter(EdgeDevice.device_id == "hb-store").all()
    assert len(rows) == 1
    assert rows[0].agent_version == "1.0.1"
    assert rows[0].trained_identity_count == 9


def test_rejected_heartbeat_is_not_stored(client, db):
    from app.models.edge_device import EdgeDevice

    response = client.post("/api/edge/v1/heartbeat", json=_heartbeat("hb-no-key"))
    assert response.status_code == 401
    assert db.query(EdgeDevice).filter(EdgeDevice.device_id == "hb-no-key").count() == 0


@pytest.mark.parametrize(
    "overrides,state",
    [
        ({}, "online"),
        ({"ai_pipeline_ready": False, "object_model_ready": False}, "degraded"),
        ({"camera_ready": False, "ai_pipeline_ready": False}, "stopped"),
    ],
)
def test_device_state(client, device_headers, teacher_client, overrides, state):
    device_id = f"hb-state-{state}"
    client.post("/api/edge/v1/heartbeat", json=_heartbeat(device_id, **overrides), headers=device_headers)

    assert _device(teacher_client, device_id)["state"] == state


def test_device_goes_offline_after_missed_heartbeats(client, device_headers, teacher_client, db):
    from app.models.edge_device import EdgeDevice
    from app.services.edge_device_service import EDGE_OFFLINE_AFTER_SECONDS

    client.post("/api/edge/v1/heartbeat", json=_heartbeat("hb-offline"), headers=device_headers)
    device = db.query(EdgeDevice).filter(EdgeDevice.device_id == "hb-offline").one()
    device.last_seen_at -= timedelta(seconds=EDGE_OFFLINE_AFTER_SECONDS + 5)
    db.commit()

    assert _device(teacher_client, "hb-offline")["state"] == "offline"


def test_device_status_api_requires_login(client):
    client.cookies.clear()
    assert client.get("/api/edge-monitoring/devices").status_code == 401


def test_device_status_api_hides_model_hashes(client, device_headers, teacher_client):
    client.post("/api/edge/v1/heartbeat", json=_heartbeat("hb-hash"), headers=device_headers)

    assert "face_model_sha256" not in _device(teacher_client, "hb-hash")
