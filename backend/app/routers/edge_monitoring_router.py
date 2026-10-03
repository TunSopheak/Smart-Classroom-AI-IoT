from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.edge_device_service import (
    EDGE_OFFLINE_AFTER_SECONDS,
    list_edge_devices,
)


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
