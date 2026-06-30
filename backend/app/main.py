from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.database.base import Base
from app.database.database import engine
from app.database.migrations import ensure_phase_16_2_schema
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
        ensure_phase_16_2_schema()
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


# Phase 12 Storage, Privacy and Admin Management routes
from app.routers.admin_router import router as phase12_admin_router
app.include_router(phase12_admin_router)


# Phase 13 Authentication and Role-Based Access
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.core.auth import (
    get_device_user_from_request,
    get_current_user_from_request,
    is_protected_path,
    is_public_path,
    user_can_access_path,
)
from app.routers.auth_router import router as phase13_auth_router

app.include_router(phase13_auth_router)
auth_templates = Jinja2Templates(directory="app/templates")


@app.middleware("http")
async def phase13_auth_middleware(request, call_next):
    path = request.url.path

    current_user = get_current_user_from_request(request) or get_device_user_from_request(request)
    request.state.current_user = current_user

    if is_public_path(path):
        return await call_next(request)

    if is_protected_path(path):
        if not current_user:
            if path.startswith("/api"):
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "message": "Authentication required.",
                    },
                )

            login_url = f"/login?next={path}"
            return RedirectResponse(url=login_url, status_code=303)

        if not user_can_access_path(current_user, path):
            if path.startswith("/api"):
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "message": "You do not have permission to access this resource.",
                    },
                )

            return auth_templates.TemplateResponse(
                request,
                "auth/access_denied.html",
                {
                    "request": request,
                    "role": current_user.get("role"),
                },
                status_code=403,
            )

    return await call_next(request)


# Phase 14 Product AI and Attendance Integration Center
from app.routers.product_integration_router import router as phase14_product_integration_router
app.include_router(phase14_product_integration_router)


# Phase 16.2 Class Groups, Courses and Weekly Schedule
from app.routers.class_setup_router import router as phase16_class_setup_router
app.include_router(phase16_class_setup_router)


# Phase 16.2.2 migration bootstrap
try:
    from app.database.database import engine
    from app.database.migrations import ensure_session_archived_column
    ensure_session_archived_column(engine)
except Exception as migration_error:
    print("Phase 16.2.2 migration warning:", migration_error)


# Phase 16.2.2 Academic lifecycle routes
from app.routers.academic_lifecycle_router import router as academic_lifecycle_router
app.include_router(academic_lifecycle_router)
