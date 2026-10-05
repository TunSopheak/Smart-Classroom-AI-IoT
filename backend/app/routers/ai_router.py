from fastapi import APIRouter

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.get("/status")
def ai_status() -> dict:
    return {
        "status": "ok",
        "message": "Face recognition and object detection run on the classroom Edge Agent.",
        "modules": ["face_recognition", "behavior_monitoring", "object_detection"],
        "edge_api": "/api/edge/v1",
    }
