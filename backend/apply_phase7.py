from pathlib import Path

ROOT = Path(__file__).resolve().parent

def write_file(relative_path: str, content: str):
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Written: {path}")

def read_file(relative_path: str):
    path = ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""

def save_file(relative_path: str, content: str):
    path = ROOT / relative_path
    path.write_text(content, encoding="utf-8")
    print(f"Updated: {path}")

write_file("app/routers/report_router.py", r"""
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
""")

write_file("app/templates/reports/index.html", r"""
{% extends "base.html" %}

{% block title %}Reports{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <p class="eyebrow">Phase 7 Reports</p>
        <h1>Reports & Export</h1>
        <p>Review attendance, AI monitoring, IoT sensor readings, and automation logs.</p>
    </div>
    <a class="btn btn-secondary" href="/dashboard">Back Dashboard</a>
</div>

<div class="report-demo-note">
    <strong>Teacher Use:</strong>
    This page helps teachers review class attendance, AI behavior events, IoT sensor data, and export CSV reports for records.
</div>

<div class="card">
    <h2>Select Session Report</h2>

    <form method="get" action="/dashboard/reports" class="ai-filter-grid">
        <div>
            <label>Session</label>
            <select name="session_id" class="form-control">
                {% for session in sessions %}
                <option value="{{ session.id }}" {% if selected_session_id == session.id %}selected{% endif %}>
                    #{{ session.id }} - {{ session.title }}
                    {% if session.active %}(Active){% else %}(Closed){% endif %}
                </option>
                {% endfor %}
            </select>
        </div>

        <div class="ai-filter-actions">
            <button class="btn btn-primary" type="submit">View Report</button>
        </div>
    </form>

    {% if selected_session %}
    <p class="muted">
        Selected: <strong>#{{ selected_session.id }} - {{ selected_session.title }}</strong>
    </p>
    {% else %}
    <p class="muted">No session selected.</p>
    {% endif %}
</div>

<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-label">Total Students</div>
        <div class="stat-value">{{ attendance_summary.total }}</div>
    </div>
    <div class="stat-card stat-success">
        <div class="stat-label">Present</div>
        <div class="stat-value">{{ attendance_summary.present }}</div>
    </div>
    <div class="stat-card stat-warning">
        <div class="stat-label">Late</div>
        <div class="stat-value">{{ attendance_summary.late }}</div>
    </div>
    <div class="stat-card stat-danger">
        <div class="stat-label">Absent</div>
        <div class="stat-value">{{ attendance_summary.absent }}</div>
    </div>
</div>

<div class="card report-actions-card">
    <div>
        <h2>Export Reports</h2>
        <p class="muted">Download CSV files for teacher record keeping.</p>
    </div>

    <div class="quick-ai-grid">
        <a class="btn btn-primary" href="/dashboard/reports/attendance.csv?session_id={{ selected_session_id }}">Export Attendance CSV</a>
        <a class="btn btn-secondary" href="/dashboard/reports/ai-events.csv?session_id={{ selected_session_id }}">Export AI Events CSV</a>
        <a class="btn btn-secondary" href="/dashboard/reports/iot-readings.csv">Export IoT Readings CSV</a>
    </div>
</div>

<div class="card">
    <h2>Attendance Report</h2>

    <div class="table-responsive">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Student</th>
                    <th>Status</th>
                    <th>Method</th>
                    <th>Confidence</th>
                    <th>First Seen</th>
                    <th>Override Reason</th>
                </tr>
            </thead>
            <tbody>
                {% for record in attendance_records %}
                <tr>
                    <td>
                        {% if record.student %}
                            <strong>{{ record.student.stu_id }}</strong><br>
                            <span class="muted">{{ record.student.name }}</span>
                        {% else %}
                            Student #{{ record.student_id }}
                        {% endif %}
                    </td>
                    <td><span class="status-badge status-{{ record.status }}">{{ record.status }}</span></td>
                    <td>{{ record.method or "-" }}</td>
                    <td>{{ "%.2f"|format(record.confidence) if record.confidence is not none else "-" }}</td>
                    <td>{{ record.first_seen_time.strftime("%Y-%m-%d %H:%M:%S") if record.first_seen_time else "-" }}</td>
                    <td>{{ record.override_reason or "-" }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="muted">No attendance records found for this session.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<div class="card">
    <h2>AI Monitoring Report</h2>

    <div class="table-responsive">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Student</th>
                    <th>Event Type</th>
                    <th>Severity</th>
                    <th>Confidence</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                {% for event in ai_events %}
                <tr>
                    <td>{{ event.created_at.strftime("%Y-%m-%d %H:%M:%S") if event.created_at else "-" }}</td>
                    <td>
                        {% if event.student %}
                            <strong>{{ event.student.stu_id }}</strong><br>
                            <span class="muted">{{ event.student.name }}</span>
                        {% else %}
                            Classroom / Unknown
                        {% endif %}
                    </td>
                    <td><span class="badge badge-ai">{{ event.event_type }}</span></td>
                    <td><span class="severity severity-{{ event.severity }}">{{ event.severity }}</span></td>
                    <td>{{ "%.2f"|format(event.confidence) if event.confidence is not none else "-" }}</td>
                    <td>{{ event.description or "-" }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="muted">No AI monitoring events found for this session.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<div class="card">
    <h2>IoT Sensor Report</h2>

    <div class="table-responsive">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Device</th>
                    <th>Temperature</th>
                    <th>Humidity</th>
                    <th>Noise</th>
                    <th>Light</th>
                </tr>
            </thead>
            <tbody>
                {% for reading in iot_readings %}
                <tr>
                    <td>{{ reading.timestamp.strftime("%Y-%m-%d %H:%M:%S") if reading.timestamp else "-" }}</td>
                    <td>{{ reading.device.name if reading.device else "Unknown Device" }}</td>
                    <td>{{ "%.1f"|format(reading.temperature) if reading.temperature is not none else "-" }}°C</td>
                    <td>{{ "%.1f"|format(reading.humidity) if reading.humidity is not none else "-" }}%</td>
                    <td>{{ "%.1f"|format(reading.noise_level) if reading.noise_level is not none else "-" }}</td>
                    <td>{{ "%.1f"|format(reading.light_level) if reading.light_level is not none else "-" }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="muted">No IoT sensor readings found.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<div class="card">
    <h2>IoT Automation Report</h2>

    <div class="table-responsive">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Rule</th>
                    <th>Action</th>
                    <th>Status</th>
                    <th>Occupancy</th>
                    <th>Reason</th>
                </tr>
            </thead>
            <tbody>
                {% for event in automation_events %}
                <tr>
                    <td>{{ event.created_at.strftime("%Y-%m-%d %H:%M:%S") if event.created_at else "-" }}</td>
                    <td><span class="badge badge-ai">{{ event.rule_name }}</span></td>
                    <td>{{ event.action }}</td>
                    <td><span class="automation-status automation-status-{{ event.status }}">{{ event.status }}</span></td>
                    <td>{{ event.occupancy_count }}</td>
                    <td>{{ event.reason or "-" }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="muted">No automation events found.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
""")

# Update main.py
main_text = read_file("app/main.py")
if "phase7_report_router" not in main_text:
    main_text += """

# Phase 7 Reports routes
from app.routers.report_router import router as phase7_report_router
app.include_router(phase7_report_router)
"""
    save_file("app/main.py", main_text)

# Update base navigation
base_text = read_file("app/templates/base.html")
if "/dashboard/reports" not in base_text:
    if "/dashboard/iot-monitoring" in base_text:
        base_text = base_text.replace(
            '<a href="/dashboard/iot-monitoring">IoT Monitoring</a>',
            '<a href="/dashboard/iot-monitoring">IoT Monitoring</a>\n    <a href="/dashboard/reports">Reports</a>',
            1,
        )
    elif "</nav>" in base_text:
        base_text = base_text.replace(
            "</nav>",
            '    <a href="/dashboard/reports">Reports</a>\n</nav>',
            1,
        )
    save_file("app/templates/base.html", base_text)

# CSS
css_text = read_file("app/static/css/styles.css")
if "Phase 7 Reports" not in css_text:
    css_text += r"""

/* Phase 7 Reports */
.report-demo-note {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    color: #0c4a6e;
    padding: 1rem 1.25rem;
    border-radius: 1rem;
    margin: 1rem 0 1.5rem;
}

.report-actions-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}

@media (max-width: 768px) {
    .report-actions-card {
        flex-direction: column;
        align-items: flex-start;
    }
}
"""
    save_file("app/static/css/styles.css", css_text)

print("")
print("DONE: Phase 7 Reports & Export System applied.")
