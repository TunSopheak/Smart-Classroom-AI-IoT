from pathlib import Path

Path("app/services/face_service.py").write_text(r'''from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import AttendanceEventResult, AttendanceMethod
from app.models.class_session import ClassSession
from app.models.face_profile import FaceProfile
from app.models.student import Student
from app.services.attendance_service import (
    calculate_attendance_status,
    ensure_attendance_records_for_session,
    get_active_session,
    get_or_create_attendance_record,
    is_student_enrolled,
    log_attendance_event,
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def get_dataset_path(student: Student) -> str:
    return student.face_dataset_path or f"ai_module/face_recognition/datasets/{student.stu_id}"


def count_dataset_images(dataset_path: str) -> int:
    path = Path(dataset_path)
    path.mkdir(parents=True, exist_ok=True)
    return len([
        file for file in path.iterdir()
        if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
    ])


def get_or_create_face_profile_summary(db: Session, student: Student) -> dict[str, Any]:
    dataset_path = get_dataset_path(student)
    sample_count = count_dataset_images(dataset_path)

    student.face_dataset_path = dataset_path

    profile = db.query(FaceProfile).filter(FaceProfile.student_id == student.id).first()

    if profile is None:
        profile = FaceProfile(
            student_id=student.id,
            dataset_path=dataset_path,
            model_label=student.id,
            sample_count=sample_count,
            trained_at=None,
        )
        db.add(profile)
    else:
        profile.dataset_path = dataset_path
        profile.model_label = student.id
        profile.sample_count = sample_count

    db.commit()
    db.refresh(student)
    db.refresh(profile)

    return {
        "id": profile.id,
        "student_id": student.id,
        "stu_id": student.stu_id,
        "student_name": student.name,
        "dataset_path": profile.dataset_path,
        "model_label": profile.model_label,
        "sample_count": profile.sample_count,
        "trained_at": profile.trained_at,
    }


def simulate_face_attendance(
    db: Session,
    student_id: int,
    session_id: int | None = None,
    confidence: float = 0.86,
    raw_source: str = "dashboard_face_simulation",
    event_time: datetime | None = None,
) -> dict[str, Any]:
    session = db.get(ClassSession, session_id) if session_id else get_active_session(db)
    if not session:
        raise ValueError("No active/session attendance session found")

    student = db.get(Student, student_id)
    if not student or not student.active:
        raise ValueError("Student not found or inactive")

    event_time = event_time or datetime.now().replace(microsecond=0)
    ensure_attendance_records_for_session(db, session)

    if not is_student_enrolled(db, session, student.id):
        event = log_attendance_event(
            db=db,
            session=session,
            student_id=student.id,
            method=AttendanceMethod.FACE,
            event_time=event_time,
            confidence=confidence,
            raw_source=raw_source,
            result=AttendanceEventResult.INVALID,
            note="Face recognized student, but student is not enrolled in this session classroom.",
        )
        db.commit()
        db.refresh(event)
        return {
            "ok": False,
            "message": f"{student.name} recognized by face but is not enrolled.",
            "result": AttendanceEventResult.INVALID.value,
            "student_id": student.id,
            "record_id": None,
            "event_id": event.id,
            "status": None,
        }

    record = get_or_create_attendance_record(db, session.id, student.id)

    if event_time > session.close_time:
        event = log_attendance_event(
            db=db,
            session=session,
            student_id=student.id,
            method=AttendanceMethod.FACE,
            event_time=event_time,
            confidence=confidence,
            raw_source=raw_source,
            result=AttendanceEventResult.AFTER_CLOSE,
            note="Face recognition was after session close time.",
        )
        db.commit()
        db.refresh(event)
        db.refresh(record)
        return {
            "ok": False,
            "message": f"{student.name} recognized after close time. Event logged only.",
            "result": AttendanceEventResult.AFTER_CLOSE.value,
            "student_id": student.id,
            "record_id": record.id,
            "event_id": event.id,
            "status": record.status,
        }

    if record.first_seen_time is not None:
        event = log_attendance_event(
            db=db,
            session=session,
            student_id=student.id,
            method=AttendanceMethod.FACE,
            event_time=event_time,
            confidence=confidence,
            raw_source=raw_source,
            result=AttendanceEventResult.DUPLICATE,
            note="Duplicate face recognition. Final attendance record was not changed.",
        )
        db.commit()
        db.refresh(event)
        db.refresh(record)
        return {
            "ok": True,
            "message": f"Duplicate face recognition for {student.name}. First seen time was kept.",
            "result": AttendanceEventResult.DUPLICATE.value,
            "student_id": student.id,
            "record_id": record.id,
            "event_id": event.id,
            "status": record.status,
        }

    status = calculate_attendance_status(event_time, session)

    record.first_seen_time = event_time
    record.status = status.value
    record.method = AttendanceMethod.FACE.value
    record.confidence = confidence
    record.override_reason = None
    record.overridden_by = None

    event = log_attendance_event(
        db=db,
        session=session,
        student_id=student.id,
        method=AttendanceMethod.FACE,
        event_time=event_time,
        confidence=confidence,
        raw_source=raw_source,
        result=AttendanceEventResult.SUCCESS,
        note=f"Face recognition accepted. Status marked as {status.value}.",
    )

    db.commit()
    db.refresh(record)
    db.refresh(event)

    return {
        "ok": True,
        "message": f"{student.name} marked as {status.value} by face recognition.",
        "result": AttendanceEventResult.SUCCESS.value,
        "student_id": student.id,
        "record_id": record.id,
        "event_id": event.id,
        "status": record.status,
    }
''', encoding="utf-8")

Path("app/schemas/face_schema.py").write_text(r'''from pydantic import BaseModel, Field


class FaceRecognitionRequest(BaseModel):
    student_id: int
    session_id: int | None = None
    confidence: float = Field(default=0.86, ge=0.0, le=1.0)
    raw_source: str = "api_face_recognition_simulation"
''', encoding="utf-8")

print("Step 1 done: face_service.py and face_schema.py created.")
