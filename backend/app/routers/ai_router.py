from fastapi import APIRouter

router = APIRouter(prefix="/api/ai", tags=["AI Placeholder"])


@router.get("/status")
def ai_status() -> dict:
    return {
        "status": "placeholder",
        "message": "AI modules will be implemented in Phase 4 and Phase 5.",
        "planned_modules": ["face_recognition", "behavior_monitoring", "object_detection"],
    }
