from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.database.base import Base
from app.database.database import engine
from app.database.seed import seed_demo_data
import app.models  # noqa: F401
from app.routers import (
    ai_router,
    attendance_router,
    classroom_router,
    dashboard_router,
    iot_router,
    session_router,
    student_router,
    subject_router,
    teacher_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Smart Classroom platform core backend for Phase 0 + Phase 1.",
    )

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.on_event("startup")
    def on_startup() -> None:
        # Development-friendly table creation.
        # Later, replace with Alembic migrations when the schema becomes stable.
        Base.metadata.create_all(bind=engine)
        seed_demo_data()

    @app.get("/health", tags=["System"])
    def health_check() -> dict:
        return {"status": "ok", "app": settings.APP_NAME, "phase": "0+1"}

    app.include_router(dashboard_router.router)
    app.include_router(student_router.router)
    app.include_router(teacher_router.router)
    app.include_router(classroom_router.router)
    app.include_router(subject_router.router)
    app.include_router(session_router.router)
    app.include_router(attendance_router.router)
    app.include_router(ai_router.router)
    app.include_router(iot_router.router)

    return app


app = create_app()


# Phase 5 AI Monitoring routes
from app.routers.ai_monitoring_router import router as phase5_ai_monitoring_router
app.include_router(phase5_ai_monitoring_router)


# Phase 7 Reports routes
from app.routers.report_router import router as phase7_report_router
app.include_router(phase7_report_router)


# Phase 8 Final Demo routes
from app.routers.demo_router import router as phase8_demo_router
app.include_router(phase8_demo_router)


# Phase 9 Camera Monitoring routes
from app.routers.camera_monitoring_router import router as phase9_camera_monitoring_router
app.include_router(phase9_camera_monitoring_router)


# Phase 11 Product Settings and Health routes
from app.routers.product_router import router as phase11_product_router
app.include_router(phase11_product_router)
