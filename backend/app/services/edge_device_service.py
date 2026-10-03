from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.edge_device import EdgeDevice
from app.schemas.edge_schema import EdgeHeartbeatRequest


# The agent sends a heartbeat every 30 seconds by default, so three missed
# heartbeats mark the device offline.
EDGE_OFFLINE_AFTER_SECONDS = 90


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def record_heartbeat(db: Session, payload: EdgeHeartbeatRequest) -> EdgeDevice:
    device = (
        db.query(EdgeDevice)
        .filter(EdgeDevice.device_id == payload.device_id)
        .first()
    )
    if device is None:
        device = EdgeDevice(device_id=payload.device_id)
        db.add(device)

    device.agent_version = payload.agent_version
    device.camera_ready = payload.camera_ready
    device.face_model_ready = payload.face_model_ready
    device.object_model_ready = payload.object_model_ready
    device.ai_pipeline_ready = payload.ai_pipeline_ready
    device.trained_identity_count = payload.trained_identity_count
    device.face_model_sha256 = payload.face_model_sha256
    device.object_model_sha256 = payload.object_model_sha256
    device.last_seen_at = _utc_now()

    db.commit()
    db.refresh(device)
    return device


def device_state(device: EdgeDevice, now: datetime | None = None) -> str:
    """Return online, degraded, stopped or offline."""
    now = now or _utc_now()
    if (now - device.last_seen_at).total_seconds() > EDGE_OFFLINE_AFTER_SECONDS:
        return "offline"
    if not device.camera_ready:
        # The agent reports camera_ready=False in its final heartbeat on shutdown.
        return "stopped"
    if not device.ai_pipeline_ready:
        return "degraded"
    return "online"


def serialize_device(device: EdgeDevice, now: datetime | None = None) -> dict[str, Any]:
    now = now or _utc_now()
    return {
        "device_id": device.device_id,
        "agent_version": device.agent_version,
        "state": device_state(device, now),
        "camera_ready": device.camera_ready,
        "face_model_ready": device.face_model_ready,
        "object_model_ready": device.object_model_ready,
        "ai_pipeline_ready": device.ai_pipeline_ready,
        "trained_identity_count": device.trained_identity_count,
        "last_seen_at": device.last_seen_at.isoformat(),
        "seconds_since_seen": max(0, int((now - device.last_seen_at).total_seconds())),
    }


def list_edge_devices(db: Session) -> list[dict[str, Any]]:
    now = _utc_now()
    devices = db.query(EdgeDevice).order_by(EdgeDevice.last_seen_at.desc()).all()
    return [serialize_device(device, now) for device in devices]
