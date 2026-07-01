from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import AttendanceEventResult, AttendanceMethod, AttendanceStatus
from app.models.attendance_event import AttendanceEvent
from app.models.attendance_record import AttendanceRecord
from app.models.academic import StudentEnrollment
from app.models.class_session import ClassSession
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.services.qr_service import parse_signed_student_qr


def calculate_attendance_status(event_time: datetime, session: ClassSession) -> AttendanceStatus:
    """Return P/L/A based on session time rules.

    P  = event_time <= late_time
    L  = late_time < event_time <= close_time
    A  = no valid event before close_time or event after close_time
    Pm = manual override only
    """
    if session.late_time is None:
        return AttendanceStatus.PRESENT

    if event_time <= session.late_time:
        return AttendanceStatus.PRESENT

    if session.close_time is None or event_time <= session.close_time:
        return AttendanceStatus.LATE

    return AttendanceStatus.ABSENT


def get_session_student_ids(db: Session, session: ClassSession) -> list[int]:
    """Return active students for the session's class group, with classroom enrollment fallback."""
    if session.class_group_id:
        return [
            item.student_id
            for item in (
                db.query(StudentEnrollment)
                .join(Student, Student.id == StudentEnrollment.student_id)
                .filter(
                    StudentEnrollment.class_group_id == session.class_group_id,
                    StudentEnrollment.active.is_(True),
                    Student.active.is_(True),
                )
                .order_by(Student.stu_id.asc())
                .all()
            )
        ]

    return [
        item.student_id
        for item in (
            db.query(Enrollment)
            .join(Student, Student.id == Enrollment.student_id)
            .filter(
                Enrollment.classroom_id == session.classroom_id,
                Enrollment.active.is_(True),
                Student.active.is_(True),
            )
            .order_by(Student.stu_id.asc())
            .all()
        )
    ]


def ensure_attendance_records_for_session(db: Session, session: ClassSession) -> list[AttendanceRecord]:
    """Create default absent records for all active students enrolled in this session."""
    student_ids = get_session_student_ids(db, session)

    records: list[AttendanceRecord] = []
    for student_id in student_ids:
        record = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.session_id == session.id,
                AttendanceRecord.student_id == student_id,
            )
            .first()
        )
        if record is None:
            record = AttendanceRecord(
                session_id=session.id,
                student_id=student_id,
                status=AttendanceStatus.ABSENT.value,
                method=AttendanceMethod.SYSTEM.value,
            )
            db.add(record)
        records.append(record)

    db.commit()
    return records


def get_active_session(db: Session) -> ClassSession | None:
    """Return the newest active class session."""
    return (
        db.query(ClassSession)
        .filter(ClassSession.active.is_(True))
        .order_by(ClassSession.start_time.desc())
        .first()
    )


def get_student_by_qr_code(db: Session, qr_code: str) -> Student | None:
    """Find active student by signed QR value, with legacy QR fallback."""
    clean_qr = qr_code.strip()
    signed_stu_id = parse_signed_student_qr(clean_qr)

    if signed_stu_id:
        return (
            db.query(Student)
            .filter(Student.stu_id == signed_stu_id, Student.active.is_(True))
            .first()
        )

    return (
        db.query(Student)
        .filter(Student.qr_code == clean_qr, Student.active.is_(True))
        .first()
    )


def is_student_enrolled(db: Session, session: ClassSession, student_id: int) -> bool:
    """Check whether a student belongs to the session class group or legacy classroom."""
    if session.class_group_id:
        return (
            db.query(StudentEnrollment)
            .filter(
                StudentEnrollment.class_group_id == session.class_group_id,
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.active.is_(True),
            )
            .first()
            is not None
        )

    return (
        db.query(Enrollment)
        .filter(
            Enrollment.classroom_id == session.classroom_id,
            Enrollment.student_id == student_id,
            Enrollment.active.is_(True),
        )
        .first()
        is not None
    )


def get_or_create_attendance_record(
    db: Session,
    session_id: int,
    student_id: int,
) -> AttendanceRecord:
    """Return existing final record or create a default Absent record."""
    record = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
        .first()
    )
    if record:
        return record

    record = AttendanceRecord(
        session_id=session_id,
        student_id=student_id,
        status=AttendanceStatus.ABSENT.value,
        method=AttendanceMethod.SYSTEM.value,
    )
    db.add(record)
    db.flush()
    return record


def is_placeholder_attendance_record(record: AttendanceRecord) -> bool:
    """Default absent rows are placeholders and can be upgraded by QR/FACE."""
    method = (record.method or AttendanceMethod.SYSTEM.value).upper()
    return (
        (record.status is None or record.status == AttendanceStatus.ABSENT.value)
        and method == AttendanceMethod.SYSTEM.value
    )


def mark_attendance_record(
    record: AttendanceRecord,
    status: AttendanceStatus,
    method: AttendanceMethod,
    event_time: datetime,
    confidence: float | None,
) -> None:
    record.first_seen_time = event_time
    record.status = status.value
    record.method = method.value
    record.confidence = confidence
    record.override_reason = None
    record.overridden_by = None
    record.updated_at = datetime.utcnow()


def log_attendance_event(
    db: Session,
    session: ClassSession,
    student_id: int | None,
    method: AttendanceMethod,
    event_time: datetime,
    confidence: float | None,
    raw_source: str | None,
    result: AttendanceEventResult,
    note: str | None = None,
) -> AttendanceEvent:
    """Store every QR/face event for audit even when invalid, unknown, or duplicate."""
    event = AttendanceEvent(
        session_id=session.id,
        student_id=student_id,
        timestamp=event_time,
        method=method.value,
        confidence=confidence,
        raw_source=raw_source,
        result=result.value,
        note=note,
    )
    db.add(event)
    db.flush()
    return event


def scan_qr_attendance(
    db: Session,
    qr_code: str,
    session_id: int | None = None,
    raw_source: str = "dashboard_qr_input",
    event_time: datetime | None = None,
) -> dict[str, Any]:
    """Process one QR scan and update final attendance safely.

    Rules:
    - Every scan is logged to attendance_events.
    - Unknown QR is logged but does not update attendance_records.
    - After close_time is logged as after_close and remains Absent unless teacher overrides.
    - Duplicate valid scans are logged but first_seen_time is preserved.
    - First valid scan updates final record to P or L.
    """
    clean_qr = qr_code.strip()
    if not clean_qr:
        raise ValueError("QR code cannot be empty")

    session = db.get(ClassSession, session_id) if session_id else get_active_session(db)
    if not session:
        raise ValueError("No active/session attendance session found")

    event_time = event_time or datetime.now().replace(microsecond=0)
    ensure_attendance_records_for_session(db, session)

    student = get_student_by_qr_code(db, clean_qr)
    if not student:
        event = log_attendance_event(
            db=db,
            session=session,
            student_id=None,
            method=AttendanceMethod.QR,
            event_time=event_time,
            confidence=None,
            raw_source=raw_source,
            result=AttendanceEventResult.UNKNOWN,
            note=f"Unknown QR code: {clean_qr}",
        )
        db.commit()
        db.refresh(event)
        return {
            "ok": False,
            "message": "Unknown QR code. Event logged, but no attendance record was updated.",
            "result": AttendanceEventResult.UNKNOWN.value,
            "student_id": None,
            "record_id": None,
            "event_id": event.id,
            "status": None,
        }

    if not is_student_enrolled(db, session, student.id):
        event = log_attendance_event(
            db=db,
            session=session,
            student_id=student.id,
            method=AttendanceMethod.QR,
            event_time=event_time,
            confidence=1.0,
            raw_source=raw_source,
            result=AttendanceEventResult.INVALID,
            note="Student exists but is not enrolled in this session class/group.",
        )
        db.commit()
        db.refresh(event)
        return {
            "ok": False,
            "message": f"{student.name} is not enrolled in this class/session. Event logged only.",
            "result": AttendanceEventResult.INVALID.value,
            "student_id": student.id,
            "record_id": None,
            "event_id": event.id,
            "status": None,
        }

    record = get_or_create_attendance_record(db, session.id, student.id)

    if session.close_time is not None and event_time > session.close_time:
        event = log_attendance_event(
            db=db,
            session=session,
            student_id=student.id,
            method=AttendanceMethod.QR,
            event_time=event_time,
            confidence=1.0,
            raw_source=raw_source,
            result=AttendanceEventResult.AFTER_CLOSE,
            note="QR scan was after session close time. Teacher override is required if accepted.",
        )
        db.commit()
        db.refresh(event)
        db.refresh(record)
        return {
            "ok": False,
            "message": f"{student.name} scanned after close time. Event logged only.",
            "result": AttendanceEventResult.AFTER_CLOSE.value,
            "student_id": student.id,
            "record_id": record.id,
            "event_id": event.id,
            "status": record.status,
        }

    if not is_placeholder_attendance_record(record):
        event = log_attendance_event(
            db=db,
            session=session,
            student_id=student.id,
            method=AttendanceMethod.QR,
            event_time=event_time,
            confidence=1.0,
            raw_source=raw_source,
            result=AttendanceEventResult.DUPLICATE,
            note="Duplicate QR scan. Final attendance record was not changed.",
        )
        db.commit()
        db.refresh(event)
        db.refresh(record)
        return {
            "ok": True,
            "message": f"Duplicate scan for {student.name}. First seen time was kept.",
            "result": AttendanceEventResult.DUPLICATE.value,
            "student_id": student.id,
            "record_id": record.id,
            "event_id": event.id,
            "status": record.status,
        }

    status = calculate_attendance_status(event_time, session)
    mark_attendance_record(
        record=record,
        status=status,
        method=AttendanceMethod.QR,
        event_time=event_time,
        confidence=1.0,
    )

    event = log_attendance_event(
        db=db,
        session=session,
        student_id=student.id,
        method=AttendanceMethod.QR,
        event_time=event_time,
        confidence=1.0,
        raw_source=raw_source,
        result=AttendanceEventResult.SUCCESS,
        note=f"QR scan accepted. Status marked as {status.value}.",
    )

    db.commit()
    db.refresh(record)
    db.refresh(event)
    return {
        "ok": True,
        "message": f"{student.name} marked as {status.value}.",
        "result": AttendanceEventResult.SUCCESS.value,
        "student_id": student.id,
        "record_id": record.id,
        "event_id": event.id,
        "status": record.status,
    }


def finalize_session_absences(db: Session, session: ClassSession) -> ClassSession:
    """Close a session and keep students without valid first_seen_time as Absent."""
    ensure_attendance_records_for_session(db, session)
    records = db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session.id).all()
    for record in records:
        if record.first_seen_time is None and record.status != AttendanceStatus.PERMISSION.value:
            record.status = AttendanceStatus.ABSENT.value
            record.method = AttendanceMethod.SYSTEM.value
    session.active = False
    db.commit()
    db.refresh(session)
    return session


def override_attendance_record(
    db: Session,
    record: AttendanceRecord,
    status: AttendanceStatus,
    overridden_by: int,
    reason: str,
) -> AttendanceRecord:
    record.status = status.value
    record.method = AttendanceMethod.MANUAL.value
    record.overridden_by = overridden_by
    record.override_reason = reason
    db.commit()
    db.refresh(record)
    return record
