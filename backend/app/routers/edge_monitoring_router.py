from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.class_session import ClassSession
from app.services.edge_device_service import (
    EDGE_OFFLINE_AFTER_SECONDS,
    list_edge_devices,
)
from app.services.edge_monitoring_service import edge_workspace_summary


# Dashboard-facing (login protected) view of Edge Agent state.
# The device-key API used by the agent itself lives in edge_router.
router = APIRouter(
    prefix="/api/edge-monitoring",
    tags=["Real AI Edge Monitoring"],
)


@router.get("/devices")
def edge_devices(db: Session = Depends(get_db)):
    devices = list_edge_devices(db)
    return {
        "offline_after_seconds": EDGE_OFFLINE_AFTER_SECONDS,
        "online_count": sum(1 for item in devices if item["state"] in {"online", "degraded"}),
        "devices": devices,
    }


@router.get("/sessions/{session_id}/summary")
def edge_session_summary(session_id: int, db: Session = Depends(get_db)):
    session = db.get(ClassSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return edge_workspace_summary(db, session)
