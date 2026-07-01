import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.ai_monitoring_event import AIMonitoringEvent
from app.models.attendance_event import AttendanceEvent
from app.models.attendance_record import AttendanceRecord
from app.models.class_session import ClassSession
from app.models.iot_automation_event import IoTAutomationEvent
from app.models.sensor_reading import SensorReading
from app.models.student import Student
from app.services.attendance_service import ensure_attendance_records_for_session

router = APIRouter(tags=["Reports"])
templates = Jinja2Templates(directory="app/templates")


ATTENDANCE_STATUSES = ["P", "L", "A", "Pm"]


def get_latest_session(db: Session):
    return db.query(ClassSession).order_by(ClassSession.start_time.desc()).first()


def get_report_session(db: Session, session_id: Optional[int]):
    if session_id:
        return db.query(ClassSession).filter(ClassSession.id == session_id).first()
    return get_latest_session(db)


def get_attendance_records(db: Session, session_id: int | None):
    if not session_id:
        return []

    return (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == session_id)
        .order_by(AttendanceRecord.student_id.asc())
        .all()
    )


def get_attendance_events(db: Session, session_id: int | None, limit: int = 30):
    if not session_id:
        return []

    return (
        db.query(AttendanceEvent)
        .filter(AttendanceEvent.session_id == session_id)
        .order_by(AttendanceEvent.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_ai_events(db: Session, session_id: int | None, limit: int = 30):
    if not session_id:
        return []

    return (
        db.query(AIMonitoringEvent)
        .filter(AIMonitoringEvent.session_id == session_id)
        .order_by(AIMonitoringEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def get_iot_readings(db: Session, limit: int = 20):
    return (
        db.query(SensorReading)
        .order_by(SensorReading.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_automation_events(db: Session, limit: int = 20):
    return (
        db.query(IoTAutomationEvent)
        .order_by(IoTAutomationEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def get_attendance_summary(records):
    summary = {
        "total": len(records),
        "present": 0,
        "late": 0,
        "absent": 0,
        "permission": 0,
        "face": 0,
        "qr": 0,
        "manual": 0,
        "system": 0,
    }

    for record in records:
        status = record.status
        method = (record.method or "").upper()

        if status == "P":
            summary["present"] += 1
        elif status == "L":
            summary["late"] += 1
        elif status == "A":
            summary["absent"] += 1
        elif status == "Pm":
            summary["permission"] += 1

        if method == "FACE":
            summary["face"] += 1
        elif method == "QR":
            summary["qr"] += 1
        elif method == "MANUAL":
            summary["manual"] += 1
        elif method == "SYSTEM":
            summary["system"] += 1

    return summary


@router.get("/dashboard/reports")
def dashboard_reports(
    request: Request,
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ClassSession)
        .order_by(ClassSession.start_time.desc())
        .limit(30)
        .all()
    )

    selected_session = get_report_session(db, session_id)
    selected_session_id = selected_session.id if selected_session else None
    if selected_session:
        ensure_attendance_records_for_session(db, selected_session)

    attendance_records = get_attendance_records(db, selected_session_id)
    attendance_events = get_attendance_events(db, selected_session_id)
    ai_events = get_ai_events(db, selected_session_id)
    iot_readings = get_iot_readings(db)
    automation_events = get_automation_events(db)
    attendance_summary = get_attendance_summary(attendance_records)

    return templates.TemplateResponse(
        request,
        "reports/index.html",
        {
            "request": request,
            "sessions": sessions,
            "selected_session": selected_session,
            "selected_session_id": selected_session_id,
            "attendance_records": attendance_records,
            "attendance_events": attendance_events,
            "ai_events": ai_events,
            "iot_readings": iot_readings,
            "automation_events": automation_events,
            "attendance_summary": attendance_summary,
        },
    )


@router.get("/dashboard/reports/attendance.csv")
def export_attendance_csv(
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    selected_session = get_report_session(db, session_id)
    selected_session_id = selected_session.id if selected_session else None
    if selected_session:
        ensure_attendance_records_for_session(db, selected_session)
    records = get_attendance_records(db, selected_session_id)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "session_id",
        "session_title",
        "student_id",
        "student_code",
        "student_name",
        "status",
        "method",
        "confidence",
        "first_seen_time",
        "overridden_by",
        "override_reason",
        "updated_at",
    ])

    for record in records:
        student = record.student if hasattr(record, "student") else None

        writer.writerow([
            selected_session_id or "",
            selected_session.title if selected_session else "",
            record.student_id,
            student.stu_id if student else "",
            student.name if student else "",
            record.status,
            record.method,
            record.confidence if record.confidence is not None else "",
            record.first_seen_time,
            record.overridden_by,
            record.override_reason,
            record.updated_at,
        ])

    filename = f"attendance_report_session_{selected_session_id or 'latest'}.csv"

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/dashboard/reports/ai-events.csv")
def export_ai_events_csv(
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    selected_session = get_report_session(db, session_id)
    selected_session_id = selected_session.id if selected_session else None
    events = get_ai_events(db, selected_session_id, limit=500)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "session_id",
        "student_id",
        "student_code",
        "student_name",
        "event_type",
        "severity",
        "confidence",
        "source",
        "description",
        "created_at",
    ])

    for event in events:
        student = event.student if hasattr(event, "student") else None

        writer.writerow([
            event.session_id,
            event.student_id or "",
            student.stu_id if student else "",
            student.name if student else "",
            event.event_type,
            event.severity,
            event.confidence if event.confidence is not None else "",
            event.source,
            event.description,
            event.created_at,
        ])

    filename = f"ai_events_report_session_{selected_session_id or 'latest'}.csv"

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/dashboard/reports/iot-readings.csv")
def export_iot_readings_csv(
    db: Session = Depends(get_db),
):
    readings = get_iot_readings(db, limit=500)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "device_id",
        "device_name",
        "temperature",
        "humidity",
        "noise_level",
        "light_level",
        "timestamp",
    ])

    for reading in readings:
        writer.writerow([
            reading.device_id,
            reading.device.name if reading.device else "",
            reading.temperature if reading.temperature is not None else "",
            reading.humidity if reading.humidity is not None else "",
            reading.noise_level if reading.noise_level is not None else "",
            reading.light_level if reading.light_level is not None else "",
            reading.timestamp,
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="iot_sensor_readings_report.csv"'
        },
    )


@router.get("/api/reports/session-summary")
def api_session_summary(
    session_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    selected_session = get_report_session(db, session_id)
    selected_session_id = selected_session.id if selected_session else None
    if selected_session:
        ensure_attendance_records_for_session(db, selected_session)

    attendance_records = get_attendance_records(db, selected_session_id)
    ai_events = get_ai_events(db, selected_session_id, limit=500)
    attendance_summary = get_attendance_summary(attendance_records)

    return {
        "session": {
            "id": selected_session.id,
            "title": selected_session.title,
            "active": selected_session.active,
            "start_time": selected_session.start_time.isoformat() if selected_session.start_time else None,
            "late_time": selected_session.late_time.isoformat() if selected_session.late_time else None,
            "close_time": selected_session.close_time.isoformat() if selected_session.close_time else None,
        } if selected_session else None,
        "attendance_summary": attendance_summary,
        "ai_events_count": len(ai_events),
    }
