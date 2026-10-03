from pathlib import Path

print("Applying Phase 2: QR Attendance Scanning + Event Logging...")

Path("app/services/attendance_service.py").write_text(r'''from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import AttendanceEventResult, AttendanceMethod, AttendanceStatus
from app.models.attendance_event import AttendanceEvent
from app.models.attendance_record import AttendanceRecord
from app.models.class_session import ClassSession
from app.models.enrollment import Enrollment
from app.models.student import Student


def calculate_attendance_status(event_time: datetime, session: ClassSession) -> AttendanceStatus:
    """Return P/L/A based on session time rules.

    P  = event_time <= late_time
    L  = late_time < event_time <= close_time
    A  = no valid event before close_time or event after close_time
    Pm = manual override only
    """
    if event_time <= session.late_time:
        return AttendanceStatus.PRESENT
    if event_time <= session.close_time:
        return AttendanceStatus.LATE
    return AttendanceStatus.ABSENT


def ensure_attendance_records_for_session(db: Session, session: ClassSession) -> list[AttendanceRecord]:
    """Create default absent records for all active students enrolled in this session's classroom."""
    enrollments = (
        db.query(Enrollment)
        .filter(
            Enrollment.classroom_id == session.classroom_id,
            Enrollment.active.is_(True),
        )
        .all()
    )

    records: list[AttendanceRecord] = []
    for enrollment in enrollments:
        record = (
            db.query(AttendanceRecord)
            .filter(
                AttendanceRecord.session_id == session.id,
                AttendanceRecord.student_id == enrollment.student_id,
            )
            .first()
        )
        if record is None:
            record = AttendanceRecord(
                session_id=session.id,
                student_id=enrollment.student_id,
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
    """Find active student by QR code value."""
    return (
        db.query(Student)
        .filter(Student.qr_code == qr_code.strip(), Student.active.is_(True))
        .first()
    )


def is_student_enrolled(db: Session, session: ClassSession, student_id: int) -> bool:
    """Check whether a student belongs to the session classroom."""
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
            note="Student exists but is not enrolled in this session classroom.",
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

    if event_time > session.close_time:
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

    if record.first_seen_time is not None:
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
    record.first_seen_time = event_time
    record.status = status.value
    record.method = AttendanceMethod.QR.value
    record.confidence = 1.0
    record.override_reason = None
    record.overridden_by = None

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
''', encoding="utf-8")

Path("app/schemas/attendance_schema.py").write_text(r'''from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import AttendanceMethod, AttendanceStatus


class AttendanceRecordRead(BaseModel):
    id: int
    session_id: int
    student_id: int
    first_seen_time: datetime | None = None
    status: AttendanceStatus
    method: AttendanceMethod
    confidence: float | None = None
    overridden_by: int | None = None
    override_reason: str | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceOverrideRequest(BaseModel):
    status: AttendanceStatus
    overridden_by: int
    override_reason: str = Field(min_length=3)


class QRScanRequest(BaseModel):
    qr_code: str = Field(min_length=1)
    session_id: int | None = None
    raw_source: str = "api_qr_scan"


class AttendanceScanResponse(BaseModel):
    ok: bool
    message: str
    result: str
    student_id: int | None = None
    record_id: int | None = None
    event_id: int | None = None
    status: AttendanceStatus | None = None


class AttendanceEventRead(BaseModel):
    id: int
    session_id: int
    student_id: int | None = None
    timestamp: datetime
    method: str
    confidence: float | None = None
    raw_source: str | None = None
    result: str
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)
''', encoding="utf-8")

Path("app/routers/attendance_router.py").write_text(r'''from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.constants import AttendanceStatus
from app.crud.attendance_crud import get_attendance_events, get_attendance_record, get_attendance_records
from app.crud.session_crud import get_session
from app.database.database import get_db
from app.schemas.attendance_schema import (
    AttendanceOverrideRequest,
    AttendanceRecordRead,
    AttendanceScanResponse,
    QRScanRequest,
)
from app.services.attendance_service import (
    ensure_attendance_records_for_session,
    override_attendance_record,
    scan_qr_attendance,
)

router = APIRouter(tags=["Attendance"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/api/sessions/{session_id}/attendance", response_model=list[AttendanceRecordRead])
def api_get_session_attendance(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ensure_attendance_records_for_session(db, session)
    return get_attendance_records(db, session_id)


@router.post("/api/attendance/scan-qr", response_model=AttendanceScanResponse)
def api_scan_qr_attendance(data: QRScanRequest, db: Session = Depends(get_db)):
    try:
        return scan_qr_attendance(
            db=db,
            qr_code=data.qr_code,
            session_id=data.session_id,
            raw_source=data.raw_source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/attendance/{record_id}/override", response_model=AttendanceRecordRead)
def api_override_attendance(record_id: int, data: AttendanceOverrideRequest, db: Session = Depends(get_db)):
    record = get_attendance_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return override_attendance_record(
        db=db,
        record=record,
        status=data.status,
        overridden_by=data.overridden_by,
        reason=data.override_reason,
    )


@router.get("/api/sessions/{session_id}/events")
def api_get_session_events(session_id: int, db: Session = Depends(get_db)):
    return get_attendance_events(db, session_id)


@router.get("/dashboard/sessions/{session_id}/attendance", response_class=HTMLResponse)
def dashboard_attendance(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ensure_attendance_records_for_session(db, session)
    return templates.TemplateResponse(
        request,
        "attendance/detail.html",
        {
            "session": session,
            "records": get_attendance_records(db, session_id),
            "events": get_attendance_events(db, session_id),
            "statuses": list(AttendanceStatus),
            "scan_result": request.query_params.get("scan_result"),
            "scan_message": request.query_params.get("scan_message"),
        },
    )


@router.post("/dashboard/attendance/scan-qr")
def dashboard_scan_qr_attendance(
    session_id: int = Form(...),
    qr_code: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        result = scan_qr_attendance(
            db=db,
            qr_code=qr_code,
            session_id=session_id,
            raw_source="dashboard_manual_qr_input",
        )
        message = result["message"].replace(" ", "+")
        return RedirectResponse(
            url=f"/dashboard/sessions/{session_id}/attendance?scan_result={result['result']}&scan_message={message}",
            status_code=303,
        )
    except ValueError as exc:
        message = str(exc).replace(" ", "+")
        return RedirectResponse(
            url=f"/dashboard/sessions/{session_id}/attendance?scan_result=error&scan_message={message}",
            status_code=303,
        )


@router.post("/dashboard/attendance/{record_id}/override")
def dashboard_override_attendance(
    record_id: int,
    status: str = Form(...),
    override_reason: str = Form(...),
    db: Session = Depends(get_db),
):
    record = get_attendance_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    override_attendance_record(
        db=db,
        record=record,
        status=AttendanceStatus(status),
        overridden_by=1,
        reason=override_reason,
    )
    return RedirectResponse(url=f"/dashboard/sessions/{record.session_id}/attendance", status_code=303)
''', encoding="utf-8")

Path("app/templates/attendance/detail.html").write_text(r'''{% extends "base.html" %}
{% block content %}
<section class="page-header">
    <div>
        <p class="eyebrow">Phase 2 Attendance</p>
        <h1>{{ session.title }}</h1>
        <p class="muted">QR scans now create attendance events and update final records per session.</p>
    </div>
</section>

{% if scan_message %}
<section class="alert alert-{{ scan_result }}">
    <strong>Scan result:</strong> {{ scan_message }}
</section>
{% endif %}

<section class="panel scan-panel">
    <h2>QR Attendance Scan</h2>
    <form class="form-row" action="/dashboard/attendance/scan-qr" method="post">
        <input type="hidden" name="session_id" value="{{ session.id }}">
        <input name="qr_code" placeholder="Paste or scan QR value, e.g. SC-STUDENT-S001" required autofocus>
        <button type="submit">Scan QR</button>
    </form>
    <p class="muted">Demo QR values: <code>SC-STUDENT-S001</code>, <code>SC-STUDENT-S002</code>, <code>SC-STUDENT-S003</code>, <code>SC-STUDENT-S004</code>, <code>SC-STUDENT-S005</code></p>
</section>

<section class="panel">
    <h2>Attendance Records</h2>
    <table>
        <thead>
            <tr><th>Student</th><th>Status</th><th>Method</th><th>First Seen</th><th>Confidence</th><th>Override</th></tr>
        </thead>
        <tbody>
        {% for record in records %}
            <tr>
                <td>
                    <strong>{{ record.student.stu_id }} - {{ record.student.name }}</strong><br>
                    <span class="small-text">QR: <code>{{ record.student.qr_code }}</code></span>
                </td>
                <td><span class="badge status-{{ record.status|lower }}">{{ record.status }}</span></td>
                <td>{{ record.method }}</td>
                <td>{{ record.first_seen_time or '-' }}</td>
                <td>{{ record.confidence or '-' }}</td>
                <td>
                    <form class="inline-form" action="/dashboard/attendance/{{ record.id }}/override" method="post">
                        <select name="status">
                            {% for status in statuses %}
                                <option value="{{ status.value }}" {% if record.status == status.value %}selected{% endif %}>{{ status.value }}</option>
                            {% endfor %}
                        </select>
                        <input name="override_reason" placeholder="Reason" required>
                        <button type="submit">Save</button>
                    </form>
                    {% if record.override_reason %}<p class="small-text">Reason: {{ record.override_reason }}</p>{% endif %}
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</section>

<section class="panel">
    <h2>Recent Attendance Events</h2>
    {% if events %}
        <table>
            <thead><tr><th>Time</th><th>Student</th><th>Method</th><th>Result</th><th>Confidence</th><th>Source</th><th>Note</th></tr></thead>
            <tbody>
            {% for event in events %}
                <tr>
                    <td>{{ event.timestamp }}</td>
                    <td>{{ event.student.name if event.student else 'Unknown' }}</td>
                    <td>{{ event.method }}</td>
                    <td><span class="event-result result-{{ event.result }}">{{ event.result }}</span></td>
                    <td>{{ event.confidence if event.confidence is not none else '-' }}</td>
                    <td>{{ event.raw_source or '-' }}</td>
                    <td class="small-text">{{ event.note or '-' }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    {% else %}
        <p class="muted">No scan events yet. Use the QR scan form above.</p>
    {% endif %}
</section>
{% endblock %}
''', encoding="utf-8")

session_router = Path("app/routers/session_router.py")
text = session_router.read_text(encoding="utf-8")

if "from app.services.attendance_service import finalize_session_absences" not in text:
    text = text.replace(
        "from app.services.session_service import prepare_session_attendance",
        "from app.services.session_service import prepare_session_attendance\nfrom app.services.attendance_service import finalize_session_absences",
    )

old_close = '''@router.post("/api/sessions/{session_id}/close", response_model=ClassSessionRead)
def api_close_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.active = False
    db.commit()
    db.refresh(session)
    return session
'''

new_close = '''@router.post("/api/sessions/{session_id}/close", response_model=ClassSessionRead)
def api_close_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return finalize_session_absences(db, session)
'''

text = text.replace(old_close, new_close)
session_router.write_text(text, encoding="utf-8")

css_path = Path("app/static/css/styles.css")
css = css_path.read_text(encoding="utf-8")

phase2_css = r'''

/* Phase 2 QR attendance UI */
.scan-panel { border-left: 5px solid var(--primary); }
.alert {
    margin-bottom: 18px;
    padding: 14px 16px;
    border-radius: 14px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
}
.alert-success { background: #ecfdf5; border-color: #bbf7d0; }
.alert-duplicate { background: #fffbeb; border-color: #fde68a; }
.alert-unknown, .alert-invalid, .alert-after_close, .alert-error { background: #fef2f2; border-color: #fecaca; }
.event-result {
    display: inline-block;
    padding: 5px 8px;
    border-radius: 999px;
    background: #e2e8f0;
    font-weight: 700;
    font-size: 12px;
}
.result-success { background: #dcfce7; color: #166534; }
.result-duplicate { background: #fef3c7; color: #92400e; }
.result-unknown, .result-invalid, .result-after_close { background: #fee2e2; color: #991b1b; }
code {
    background: #f1f5f9;
    padding: 3px 6px;
    border-radius: 6px;
}
'''

if "/* Phase 2 QR attendance UI */" not in css:
    css_path.write_text(css + phase2_css, encoding="utf-8")

print("DONE: Phase 2 files updated.")
print("Updated:")
print("- app/services/attendance_service.py")
print("- app/schemas/attendance_schema.py")
print("- app/routers/attendance_router.py")
print("- app/routers/session_router.py")
print("- app/templates/attendance/detail.html")
print("- app/static/css/styles.css")
