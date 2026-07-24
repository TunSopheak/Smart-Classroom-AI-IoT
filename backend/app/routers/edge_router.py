from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.auth import is_valid_device_api_key
from app.database.database import get_db
from app.models.class_session import ClassSession
from app.models.student import Student
from app.schemas.edge_schema import (
    EdgeContextResponse,
    EdgeHeartbeatRequest,
    EdgeSessionContext,
    EdgeStudentContext,
)
from app.services.attendance_service import is_student_enrolled
from app.services.face_service import FACE_ATTENDANCE_MIN_CONFIDENCE


router = APIRouter(
    prefix="/api/edge/v1",
    tags=["Real AI Edge"],
)


def require_edge_device(request: Request) -> dict:
    provided_key = request.headers.get(
        "x-smart-classroom-device-key",
        "",
    )

    if not is_valid_device_api_key(provided_key):
        raise HTTPException(
            status_code=401,
            detail="Valid classroom device key required.",
        )

    return {
        "device_authenticated": True,
    }


@router.post("/heartbeat")
def edge_heartbeat(
    payload: EdgeHeartbeatRequest,
    authenticated_device: dict = Depends(require_edge_device),
):
    components = {
        "camera": payload.camera_ready,
        "face_model": payload.face_model_ready,
        "object_model": payload.object_model_ready,
        "ai_pipeline": payload.ai_pipeline_ready,
    }

    return {
        "success": True,
        "api_version": "edge-v1",
        "device_authenticated": bool(
            authenticated_device["device_authenticated"]
        ),
        "device_id": payload.device_id,
        "agent_version": payload.agent_version,
        "status": "ready" if all(components.values()) else "degraded",
        "components": components,
        "trained_identity_count": payload.trained_identity_count,
        "server_timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/context",
    response_model=EdgeContextResponse,
)
def edge_context(
    authenticated_device: dict = Depends(require_edge_device),
    db: Session = Depends(get_db),
):
    del authenticated_device

    active_session = (
        db.query(ClassSession)
        .filter(ClassSession.active == True)
        .order_by(ClassSession.start_time.desc())
        .first()
    )

    session_context = None

    if active_session is not None:
        students = (
            db.query(Student)
            .filter(Student.active == True)
            .order_by(Student.stu_id.asc())
            .all()
        )

        enrolled_students = []

        for student in students:
            if not is_student_enrolled(
                db,
                active_session,
                student.id,
            ):
                continue

            enrolled_students.append(
                EdgeStudentContext(
                    stu_id=student.stu_id,
                    name=student.name,
                )
            )

        session_context = EdgeSessionContext(
            session_id=active_session.id,
            title=active_session.title,
            start_time=active_session.start_time,
            late_time=active_session.late_time,
            close_time=active_session.close_time,
            students=enrolled_students,
        )

    return EdgeContextResponse(
        api_version="edge-v1",
        server_timestamp=datetime.now(timezone.utc),
        attendance_face_threshold=FACE_ATTENDANCE_MIN_CONFIDENCE,
        active_session=session_context,
    )
