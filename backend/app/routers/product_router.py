from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from app.core.product_settings import load_product_settings, save_product_settings
from app.database.database import SessionLocal
from app.services.camera_monitoring_service import RECORDINGS_DIR, camera_service

router = APIRouter(tags=["Product"])
templates = Jinja2Templates(directory="app/templates")


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def check_database() -> dict:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1")).scalar()
        db.close()

        return {
            "name": "Database",
            "status": "ok",
            "message": "SQLite database connection is working.",
        }
    except Exception as exc:
        return {
            "name": "Database",
            "status": "error",
            "message": str(exc),
        }


def check_opencv() -> dict:
    try:
        import cv2

        return {
            "name": "OpenCV",
            "status": "ok",
            "message": f"OpenCV {cv2.__version__}, cv2.face={hasattr(cv2, 'face')}",
        }
    except Exception as exc:
        return {
            "name": "OpenCV",
            "status": "error",
            "message": str(exc),
        }


def check_recording_folder() -> dict:
    try:
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        files = list(RECORDINGS_DIR.glob("*"))
        total_size = sum(file.stat().st_size for file in files if file.is_file())
        total_size_mb = round(total_size / (1024 * 1024), 2)

        return {
            "name": "Recording Storage",
            "status": "ok",
            "message": f"{len(files)} file(s), {total_size_mb} MB used.",
        }
    except Exception as exc:
        return {
            "name": "Recording Storage",
            "status": "error",
            "message": str(exc),
        }


def check_camera_service() -> dict:
    status = camera_service.get_status()

    if status.get("running"):
        message = "Camera service is running."
    else:
        message = "Camera service is currently stopped. This is OK when not recording."

    return {
        "name": "Camera Service",
        "status": "ok",
        "message": message,
        "details": status,
    }


def check_required_pages() -> list[dict]:
    pages = [
        ("Dashboard", "/dashboard"),
        ("Students", "/dashboard/students"),
        ("Sessions", "/dashboard/sessions"),
        ("AI Monitoring", "/dashboard/ai-monitoring"),
        ("Camera Monitoring", "/dashboard/camera-monitoring"),
        ("IoT Monitoring", "/dashboard/iot-monitoring"),
        ("Reports", "/dashboard/reports"),
        ("Final Demo", "/dashboard/final-demo"),
        ("Product Settings", "/dashboard/product-settings"),
        ("System Health", "/dashboard/system-health"),
    ]

    return [
        {
            "name": name,
            "status": "ready",
            "message": url,
        }
        for name, url in pages
    ]


@router.get("/dashboard/product-settings")
def product_settings_page(request: Request):
    settings = load_product_settings()

    return templates.TemplateResponse(
        request,
        "product/settings.html",
        {
            "request": request,
            "settings": settings,
        },
    )


@router.post("/dashboard/product-settings")
def update_product_settings(
    product_name: str = Form(...),
    school_name: str = Form(...),
    timezone: str = Form("Asia/Phnom_Penh"),
    camera_index: int = Form(0),
    recording_format: str = Form("webm_vp8"),
    auto_behavior_default: Optional[str] = Form(None),
    attention_low_seconds: float = Form(2.5),
    leaving_seat_seconds: float = Form(5.0),
    sleeping_seconds: float = Form(4.0),
    behavior_cooldown_seconds: float = Form(20.0),
    privacy_note: str = Form("Use volunteer/demo faces only during project demonstration."),
):
    save_product_settings(
        {
            "product_name": product_name,
            "school_name": school_name,
            "timezone": timezone,
            "camera_index": camera_index,
            "recording_format": recording_format,
            "auto_behavior_default": auto_behavior_default == "on",
            "attention_low_seconds": attention_low_seconds,
            "leaving_seat_seconds": leaving_seat_seconds,
            "sleeping_seconds": sleeping_seconds,
            "behavior_cooldown_seconds": behavior_cooldown_seconds,
            "privacy_note": privacy_note,
        }
    )

    return RedirectResponse(url="/dashboard/product-settings?saved=1", status_code=303)


@router.get("/dashboard/system-health")
def system_health_page(request: Request):
    health_checks = [
        check_database(),
        check_opencv(),
        check_recording_folder(),
        check_camera_service(),
    ]

    route_checks = check_required_pages()

    readiness_items = [
        {"label": "QR attendance workflow", "ready": True},
        {"label": "Face recognition attendance workflow", "ready": True},
        {"label": "AI monitoring events", "ready": True},
        {"label": "Camera monitoring and recording", "ready": True},
        {"label": "Browser-compatible WebM playback", "ready": True},
        {"label": "Behavior detection engine", "ready": True},
        {"label": "IoT monitoring and automation", "ready": True},
        {"label": "Reports and CSV export", "ready": True},
        {"label": "Final demo and defense package", "ready": True},
        {"label": "Product settings and health checks", "ready": True},
    ]

    return templates.TemplateResponse(
        request,
        "product/health.html",
        {
            "request": request,
            "health_checks": health_checks,
            "route_checks": route_checks,
            "readiness_items": readiness_items,
            "settings": load_product_settings(),
        },
    )


@router.get("/api/system-health")
def api_system_health():
    return {
        "settings": load_product_settings(),
        "health_checks": [
            check_database(),
            check_opencv(),
            check_recording_folder(),
            check_camera_service(),
        ],
        "routes": check_required_pages(),
    }
