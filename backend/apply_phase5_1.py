from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"Updated: {path}")

# 1) Update AI monitoring service filters
service_path = ROOT / "app/services/ai_monitoring_service.py"
service_text = r'''
from sqlalchemy.orm import Session

from app.models.ai_monitoring_event import AIMonitoringEvent
from app.schemas.ai_monitoring_schema import AIMonitoringEventCreate


def _payload_to_dict(payload: AIMonitoringEventCreate) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


def create_ai_monitoring_event(db: Session, payload: AIMonitoringEventCreate) -> AIMonitoringEvent:
    data = _payload_to_dict(payload)

    confidence = data.get("confidence")
    if confidence is not None:
        confidence = round(float(confidence), 2)

    event = AIMonitoringEvent(
        session_id=data.get("session_id"),
        student_id=data.get("student_id"),
        event_type=str(data.get("event_type")).strip().lower(),
        severity=str(data.get("severity") or "info").strip().lower(),
        confidence=confidence,
        source=str(data.get("source") or "manual_simulation").strip(),
        description=data.get("description"),
    )

    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_ai_monitoring_events(
    db: Session,
    session_id: int | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    limit: int = 100,
):
    query = db.query(AIMonitoringEvent)

    if session_id:
        query = query.filter(AIMonitoringEvent.session_id == session_id)

    if event_type:
        query = query.filter(AIMonitoringEvent.event_type == event_type)

    if severity:
        query = query.filter(AIMonitoringEvent.severity == severity)

    return query.order_by(AIMonitoringEvent.created_at.desc()).limit(limit).all()


def get_ai_monitoring_stats(events):
    stats = {
        "total": len(events),
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
        "phone_usage": 0,
        "sleeping": 0,
        "leaving_seat": 0,
        "hand_raising": 0,
        "attention_low": 0,
    }

    for event in events:
        severity = (event.severity or "info").lower()
        event_type = (event.event_type or "").lower()

        if severity in stats:
            stats[severity] += 1

        if event_type in stats:
            stats[event_type] += 1

    return stats
'''
write(service_path, service_text.strip() + "\n")

# 2) Update AI monitoring router with filters
router_path = ROOT / "app/routers/ai_monitoring_router.py"
router_text = r'''
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.class_session import ClassSession
from app.models.student import Student
from app.schemas.ai_monitoring_schema import AIMonitoringEventCreate
from app.services.ai_monitoring_service import (
    create_ai_monitoring_event,
    get_ai_monitoring_stats,
    list_ai_monitoring_events,
)

router = APIRouter(tags=["AI Monitoring"])
templates = Jinja2Templates(directory="app/templates")

EVENT_TYPES = [
    "phone_usage",
    "sleeping",
    "leaving_seat",
    "hand_raising",
    "attention_low",
]

SEVERITIES = [
    "info",
    "low",
    "medium",
    "high",
]


def event_to_dict(event):
    return {
        "id": event.id,
        "session_id": event.session_id,
        "student_id": event.student_id,
        "student": {
            "id": event.student.id,
            "stu_id": event.student.stu_id,
            "name": event.student.name,
        } if event.student else None,
        "event_type": event.event_type,
        "severity": event.severity,
        "confidence": event.confidence,
        "source": event.source,
        "description": event.description,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.get("/api/ai-monitoring/events")
def api_list_ai_events(
    session_id: Optional[int] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    events = list_ai_monitoring_events(
        db,
        session_id=session_id,
        event_type=event_type or None,
        severity=severity or None,
        limit=limit,
    )
    return [event_to_dict(event) for event in events]


@router.post("/api/ai-monitoring/events")
def api_create_ai_event(
    payload: AIMonitoringEventCreate,
    db: Session = Depends(get_db),
):
    event = create_ai_monitoring_event(db, payload)
    return {
        "success": True,
        "message": "AI monitoring event logged successfully.",
        "event": event_to_dict(event),
    }


@router.post("/api/ai-monitoring/simulate")
def api_simulate_ai_event(
    payload: AIMonitoringEventCreate,
    db: Session = Depends(get_db),
):
    event = create_ai_monitoring_event(db, payload)
    return {
        "success": True,
        "message": f"Simulated AI event: {event.event_type}",
        "event": event_to_dict(event),
    }


@router.get("/dashboard/ai-monitoring")
def dashboard_ai_monitoring(
    request: Request,
    session_id: Optional[int] = None,
    event_type: str = "",
    severity: str = "",
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ClassSession)
        .order_by(ClassSession.start_time.desc())
        .limit(20)
        .all()
    )

    active_session = (
        db.query(ClassSession)
        .filter(ClassSession.active == True)
        .order_by(ClassSession.start_time.desc())
        .first()
    )

    selected_session_id = session_id
    if selected_session_id is None and active_session:
        selected_session_id = active_session.id
    elif selected_session_id is None and sessions:
        selected_session_id = sessions[0].id

    students = db.query(Student).order_by(Student.stu_id.asc()).all()

    events = list_ai_monitoring_events(
        db,
        session_id=selected_session_id,
        event_type=event_type or None,
        severity=severity or None,
        limit=100,
    )

    stats = get_ai_monitoring_stats(events)

    return templates.TemplateResponse(
        request,
        "ai_monitoring/index.html",
        {
            "request": request,
            "sessions": sessions,
            "students": students,
            "events": events,
            "stats": stats,
            "event_types": EVENT_TYPES,
            "severities": SEVERITIES,
            "selected_session_id": selected_session_id,
            "active_session": active_session,
            "selected_event_type": event_type,
            "selected_severity": severity,
        },
    )


@router.post("/dashboard/ai-monitoring/simulate")
def dashboard_simulate_ai_event(
    session_id: int = Form(...),
    student_id: str = Form(""),
    event_type: str = Form(...),
    severity: str = Form("info"),
    confidence: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    parsed_student_id = int(student_id) if student_id else None

    parsed_confidence = None
    if confidence:
        try:
            parsed_confidence = float(confidence)
        except ValueError:
            parsed_confidence = None

    payload = AIMonitoringEventCreate(
        session_id=session_id,
        student_id=parsed_student_id,
        event_type=event_type,
        severity=severity,
        confidence=parsed_confidence,
        source="dashboard_manual_simulation",
        description=description or f"Manual simulation for {event_type}",
    )

    create_ai_monitoring_event(db, payload)

    return RedirectResponse(
        url=f"/dashboard/ai-monitoring?session_id={session_id}",
        status_code=303,
    )
'''
write(router_path, router_text.strip() + "\n")

# 3) Update AI monitoring template
template_path = ROOT / "app/templates/ai_monitoring/index.html"
template_text = r'''
{% extends "base.html" %}

{% block title %}AI Monitoring{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <p class="eyebrow">Phase 5.1 AI Monitoring</p>
        <h1>AI Monitoring</h1>
        <p>Log, filter, and review AI classroom behavior events for each class session.</p>
    </div>
    <a class="btn btn-secondary" href="/dashboard">Back Dashboard</a>
</div>

<div class="ai-demo-note">
    <strong>Demo Purpose:</strong>
    This page is the foundation for future YOLO / MediaPipe detection. For now, teachers can simulate and review AI events such as phone usage, sleeping, leaving seat, hand raising, and low attention.
</div>

<div class="stats-grid ai-stats-grid">
    <div class="stat-card">
        <div class="stat-label">Total AI Events</div>
        <div class="stat-value">{{ stats.total }}</div>
    </div>
    <div class="stat-card stat-danger">
        <div class="stat-label">High Severity</div>
        <div class="stat-value">{{ stats.high }}</div>
    </div>
    <div class="stat-card stat-warning">
        <div class="stat-label">Phone Usage</div>
        <div class="stat-value">{{ stats.phone_usage }}</div>
    </div>
    <div class="stat-card stat-danger">
        <div class="stat-label">Attention Low</div>
        <div class="stat-value">{{ stats.attention_low }}</div>
    </div>
</div>

<div class="card">
    <h2>Filter Events</h2>

    <form method="get" action="/dashboard/ai-monitoring" class="ai-filter-grid">
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

        <div>
            <label>Event Type</label>
            <select name="event_type" class="form-control">
                <option value="">All event types</option>
                {% for item in event_types %}
                <option value="{{ item }}" {% if selected_event_type == item %}selected{% endif %}>{{ item }}</option>
                {% endfor %}
            </select>
        </div>

        <div>
            <label>Severity</label>
            <select name="severity" class="form-control">
                <option value="">All severities</option>
                {% for item in severities %}
                <option value="{{ item }}" {% if selected_severity == item %}selected{% endif %}>{{ item }}</option>
                {% endfor %}
            </select>
        </div>

        <div class="ai-filter-actions">
            <button class="btn btn-primary" type="submit">Apply Filter</button>
            <a class="btn btn-secondary" href="/dashboard/ai-monitoring">Reset</a>
        </div>
    </form>

    {% if not sessions %}
    <p class="muted">No session found. Please create a class session first.</p>
    {% endif %}
</div>

<div class="card">
    <h2>Quick AI Event Simulation</h2>
    <p class="muted">Classroom-level quick buttons. These are useful for fast demo testing.</p>

    {% if selected_session_id %}
    <div class="quick-ai-grid">
        <form method="post" action="/dashboard/ai-monitoring/simulate">
            <input type="hidden" name="session_id" value="{{ selected_session_id }}">
            <input type="hidden" name="event_type" value="phone_usage">
            <input type="hidden" name="severity" value="medium">
            <input type="hidden" name="confidence" value="0.86">
            <input type="hidden" name="description" value="Student may be using phone during class.">
            <button class="btn btn-warning" type="submit">Phone Usage</button>
        </form>

        <form method="post" action="/dashboard/ai-monitoring/simulate">
            <input type="hidden" name="session_id" value="{{ selected_session_id }}">
            <input type="hidden" name="event_type" value="sleeping">
            <input type="hidden" name="severity" value="high">
            <input type="hidden" name="confidence" value="0.82">
            <input type="hidden" name="description" value="Student may be sleeping or not paying attention.">
            <button class="btn btn-danger" type="submit">Sleeping</button>
        </form>

        <form method="post" action="/dashboard/ai-monitoring/simulate">
            <input type="hidden" name="session_id" value="{{ selected_session_id }}">
            <input type="hidden" name="event_type" value="leaving_seat">
            <input type="hidden" name="severity" value="medium">
            <input type="hidden" name="confidence" value="0.78">
            <input type="hidden" name="description" value="Student may have left their seat.">
            <button class="btn btn-warning" type="submit">Leaving Seat</button>
        </form>

        <form method="post" action="/dashboard/ai-monitoring/simulate">
            <input type="hidden" name="session_id" value="{{ selected_session_id }}">
            <input type="hidden" name="event_type" value="hand_raising">
            <input type="hidden" name="severity" value="info">
            <input type="hidden" name="confidence" value="0.91">
            <input type="hidden" name="description" value="Student raised hand.">
            <button class="btn btn-secondary" type="submit">Hand Raising</button>
        </form>

        <form method="post" action="/dashboard/ai-monitoring/simulate">
            <input type="hidden" name="session_id" value="{{ selected_session_id }}">
            <input type="hidden" name="event_type" value="attention_low">
            <input type="hidden" name="severity" value="high">
            <input type="hidden" name="confidence" value="0.80">
            <input type="hidden" name="description" value="Student attention level appears low.">
            <button class="btn btn-danger" type="submit">Attention Low</button>
        </form>
    </div>
    {% else %}
    <p class="muted">Please create a session first.</p>
    {% endif %}
</div>

<div class="card">
    <h2>Student-Specific Quick Event</h2>
    <p class="muted">Use this when the teacher wants to attach an AI event to a real student.</p>

    {% if selected_session_id %}
    <form method="post" action="/dashboard/ai-monitoring/simulate" class="ai-form-grid">
        <input type="hidden" name="session_id" value="{{ selected_session_id }}">

        <div>
            <label>Student</label>
            <select name="student_id" class="form-control">
                <option value="">Classroom-level / Unknown</option>
                {% for student in students %}
                <option value="{{ student.id }}">{{ student.stu_id }} - {{ student.name }}</option>
                {% endfor %}
            </select>
        </div>

        <div>
            <label>Event Type</label>
            <select name="event_type" class="form-control">
                {% for event_type in event_types %}
                <option value="{{ event_type }}">{{ event_type }}</option>
                {% endfor %}
            </select>
        </div>

        <div>
            <label>Severity</label>
            <select name="severity" class="form-control">
                {% for severity in severities %}
                <option value="{{ severity }}">{{ severity }}</option>
                {% endfor %}
            </select>
        </div>

        <div>
            <label>Confidence</label>
            <input class="form-control" type="number" step="0.01" min="0" max="1" name="confidence" value="0.80">
        </div>

        <div class="ai-form-full">
            <label>Description</label>
            <input class="form-control" type="text" name="description" placeholder="Example: S001 looked at phone during explanation.">
        </div>

        <div class="ai-form-full">
            <button class="btn btn-primary" type="submit">Log Student AI Event</button>
        </div>
    </form>
    {% else %}
    <p class="muted">Please create a session first.</p>
    {% endif %}
</div>

<div class="card">
    <h2>AI Event History</h2>

    <div class="table-responsive">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Student</th>
                    <th>Event Type</th>
                    <th>Severity</th>
                    <th>Confidence</th>
                    <th>Source</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                {% for event in events %}
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
                    <td>{{ event.source }}</td>
                    <td>{{ event.description or "-" }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="7" class="muted">No AI monitoring events yet.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
'''
write(template_path, template_text.strip() + "\n")

# 4) Add AI monitoring link card into attendance detail
attendance_path = ROOT / "app/templates/attendance/detail.html"
attendance_text = read(attendance_path)

if "Phase 5.1 AI Monitoring Link" not in attendance_text:
    insert_block = r'''
<!-- Phase 5.1 AI Monitoring Link -->
<div class="card ai-session-link-card">
    <div>
        <h2>AI Monitoring Events</h2>
        <p class="muted">Review phone usage, sleeping, leaving seat, hand raising, and low attention events for this session.</p>
    </div>
    <a class="btn btn-primary" href="/dashboard/ai-monitoring?session_id={{ session.id }}">Open AI Monitoring</a>
</div>
'''
    if "{% endblock %}" in attendance_text:
        attendance_text = attendance_text.replace("{% endblock %}", insert_block + "\n{% endblock %}")
    else:
        attendance_text += "\n" + insert_block
    write(attendance_path, attendance_text)

# 5) CSS polish
css_path = ROOT / "app/static/css/styles.css"
css_text = read(css_path)

if "Phase 5.1 AI Monitoring Polish" not in css_text:
    css_text += r'''

/* Phase 5.1 AI Monitoring Polish */
.eyebrow {
    color: #2563eb;
    font-size: 0.8rem;
    text-transform: uppercase;
    font-weight: 800;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}

.ai-demo-note {
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    color: #1e1b4b;
    padding: 1rem 1.25rem;
    border-radius: 1rem;
    margin: 1rem 0 1.5rem;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1rem;
}

.stat-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 1rem;
    padding: 1.1rem 1.25rem;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
}

.stat-label {
    color: #64748b;
    font-size: 0.9rem;
    font-weight: 700;
}

.stat-value {
    color: #0f172a;
    font-size: 2rem;
    font-weight: 900;
    margin-top: 0.4rem;
}

.stat-warning {
    border-color: #fde68a;
    background: #fffbeb;
}

.stat-danger {
    border-color: #fecaca;
    background: #fef2f2;
}

.ai-filter-grid {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr auto;
    gap: 1rem;
    align-items: end;
}

.ai-filter-actions {
    display: flex;
    gap: 0.5rem;
}

.ai-session-link-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}

@media (max-width: 1000px) {
    .stats-grid,
    .ai-filter-grid {
        grid-template-columns: 1fr 1fr;
    }
}

@media (max-width: 700px) {
    .stats-grid,
    .ai-filter-grid {
        grid-template-columns: 1fr;
    }

    .ai-session-link-card {
        flex-direction: column;
        align-items: flex-start;
    }
}
'''
    write(css_path, css_text)

print("DONE: Phase 5.1 polish applied.")
