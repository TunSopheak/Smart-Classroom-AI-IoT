from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401  (registers every model with Base.metadata)
from app.core.auth_middleware import auth_middleware
from app.core.config import settings
from app.database.base import Base
from app.database.database import engine
from app.database.migrations import apply_schema_migrations
from app.database.seed import seed_demo_data
from app.routers import (
    academic_lifecycle_router,
    admin_router,
    ai_monitoring_router,
    ai_router,
    attendance_router,
    auth_router,
    camera_monitoring_router,
    class_setup_router,
    classroom_router,
    dashboard_router,
    demo_router,
    edge_monitoring_router,
    edge_router,
    iot_router,
    object_detection_page_router,
    object_detection_router,
    object_detection_stream_router,
    product_integration_router,
    product_router,
    report_router,
    session_router,
    student_router,
    subject_router,
    teacher_router,
)


# Registration order matters: when two routers declare the same path,
# the first one registered wins.
ROUTERS = (
    # Core academic data
    dashboard_router,
    student_router,
    teacher_router,
    classroom_router,
    subject_router,
    session_router,
    attendance_router,
    ai_router,
    iot_router,
    # Monitoring, reports and administration
    ai_monitoring_router,
    report_router,
    demo_router,
    camera_monitoring_router,
    product_router,
    admin_router,
    auth_router,
    product_integration_router,
    class_setup_router,
    academic_lifecycle_router,
    # Object detection
    object_detection_router,
    object_detection_stream_router,
    object_detection_page_router,
    # Real AI Edge-to-Cloud
    edge_router,
    edge_monitoring_router,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # create_all() only creates missing tables; apply_schema_migrations()
    # adds columns introduced after a database was first created.
    Base.metadata.create_all(bind=engine)
    apply_schema_migrations()
    seed_demo_data()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version="1.1.0",
        description=(
            "Smart Classroom platform: attendance, AI monitoring, IoT and "
            "the real AI Edge-to-Cloud API."
        ),
        lifespan=lifespan,
    )

    static_dir = Path(__file__).parent / "static"
    application.mount("/static", StaticFiles(directory=static_dir), name="static")

    @application.get("/", include_in_schema=False)
    def root_redirect():
        return RedirectResponse(url="/login", status_code=303)

    @application.get("/health", tags=["System"])
    def health_check() -> dict:
        return {"status": "ok", "app": settings.APP_NAME}

    for module in ROUTERS:
        application.include_router(module.router)

    application.middleware("http")(auth_middleware)
    return application


app = create_app()
