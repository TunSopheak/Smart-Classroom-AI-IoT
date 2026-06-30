from fastapi import APIRouter

from app.services.object_detection_service import object_detection_service

router = APIRouter(tags=["Object Detection"])


@router.get("/api/object-detection/status")
def get_object_detection_status():
    return object_detection_service.status()
