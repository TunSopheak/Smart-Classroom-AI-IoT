from pathlib import Path

ROOT = Path(__file__).resolve().parent

def write_file(relative_path: str, content: str):
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Written: {path}")

write_file("app/models/ai_monitoring_event.py", r"""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class AIMonitoringEvent(Base):
    __tablename__ = "ai_monitoring_events"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(Integer, ForeignKey("class_sessions.id"), nullable=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)

    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="info", index=True)
    confidence = Column(Float, nullable=True)

    source = Column(String(80), nullable=False, default="manual_simulation")
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    session = relationship("ClassSession")
    student = relationship("Student")
""")

write_file("app/schemas/ai_monitoring_schema.py", r"""
from typing import Optional

from pydantic import BaseModel, Field


class AIMonitoringEventCreate(BaseModel):
    session_id: Optional[int] = None
    student_id: Optional[int] = None
    event_type: str = Field(..., min_length=2, max_length=50)
    severity: str = Field(default="info", max_length=20)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    source: str = Field(default="manual_simulation", max_length=80)
    description: Optional[str] = None


class AIMonitoringEventRead(BaseModel):
    id: int
    session_id: Optional[int]
    student_id: Optional[int]
    event_type: str
    severity: str
    confidence: Optional[float]
    source: str
    description: Optional[str]

    class Config:
        orm_mode = True
""")

write_file("app/services/ai_monitoring_service.py", r"""
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


def list_ai_monitoring_events(db: Session, session_id: int | None = None, limit: int = 100):
    query = db.query(AIMonitoringEvent)

    if session_id:
        query = query.filter(AIMonitoringEvent.session_id == session_id)

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
""")

write_file("app/routers/ai_monitoring_router.py", r"""
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
    limit: int = 100,
    db: Session = Depends(get_db),
):
    events = list_ai_monitoring_events(db, session_id=session_id, limit=limit)
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
""")

write_file("app/templates/ai_monitoring/index.html", r"""
{% extends "base.html" %}

{% block title %}AI Monitoring{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <h1>AI Monitoring</h1>
        <p>Log and review AI classroom behavior events for each session.</p>
    </div>
    <a class="btn btn-secondary" href="/dashboard">Back Dashboard</a>
</div>

<div class="stats-grid ai-stats-grid">
    <div class="stat-card">
        <div class="stat-label">Total AI Events</div>
        <div class="stat-value">{{ stats.total }}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">High Severity</div>
        <div class="stat-value">{{ stats.high }}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Phone Usage</div>
        <div class="stat-value">{{ stats.phone_usage }}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Attention Low</div>
        <div class="stat-value">{{ stats.attention_low }}</div>
    </div>
</div>

<div class="card">
    <h2>Select Session</h2>

    <form method="get" action="/dashboard/ai-monitoring" class="form-row">
        <select name="session_id" class="form-control">
            {% for session in sessions %}
            <option value="{{ session.id }}" {% if selected_session_id == session.id %}selected{% endif %}>
                #{{ session.id }} - {{ session.title }}
                {% if session.active %}(Active){% else %}(Closed){% endif %}
            </option>
            {% endfor %}
        </select>

        <button class="btn btn-primary" type="submit">View Events</button>
    </form>

    {% if not sessions %}
    <p class="muted">No session found. Please create a class session first.</p>
    {% endif %}
</div>

<div class="card">
    <h2>Quick AI Event Simulation</h2>
    <p class="muted">Use this for demo/testing before connecting real MediaPipe or YOLO detection.</p>

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
    <h2>Manual AI Event Log</h2>

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
            <input class="form-control" type="text" name="description" placeholder="Example: Student looked at phone during explanation.">
        </div>

        <div class="ai-form-full">
            <button class="btn btn-primary" type="submit">Log AI Event</button>
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
                            {{ event.student.stu_id }} - {{ event.student.name }}
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
""")

# Update app/models/__init__.py
models_init = ROOT / "app/models/__init__.py"
models_text = models_init.read_text(encoding="utf-8") if models_init.exists() else ""
if "ai_monitoring_event" not in models_text:
    models_text += "\nfrom app.models.ai_monitoring_event import AIMonitoringEvent\n"
    models_init.write_text(models_text, encoding="utf-8")
    print("Updated: app/models/__init__.py")

# Update app/main.py safely
main_path = ROOT / "app/main.py"
main_text = main_path.read_text(encoding="utf-8")
if "phase5_ai_monitoring_router" not in main_text:
    main_text += """

# Phase 5 AI Monitoring routes
from app.routers.ai_monitoring_router import router as phase5_ai_monitoring_router
app.include_router(phase5_ai_monitoring_router)
"""
    main_path.write_text(main_text, encoding="utf-8")
    print("Updated: app/main.py")

# Update base navigation if possible
base_path = ROOT / "app/templates/base.html"
if base_path.exists():
    base_text = base_path.read_text(encoding="utf-8")
    if "/dashboard/ai-monitoring" not in base_text:
        if "</nav>" in base_text:
            base_text = base_text.replace(
                "</nav>",
                '    <a href="/dashboard/ai-monitoring">AI Monitoring</a>\n</nav>',
                1,
            )
        else:
            base_text += '\n<!-- Phase 5 AI Monitoring: /dashboard/ai-monitoring -->\n'
        base_path.write_text(base_text, encoding="utf-8")
        print("Updated: app/templates/base.html")

# Append CSS
css_path = ROOT / "app/static/css/styles.css"
css_text = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
if "Phase 5 AI Monitoring" not in css_text:
    css_text += r"""

/* Phase 5 AI Monitoring */
.ai-stats-grid {
    margin-bottom: 1.5rem;
}

.quick-ai-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-top: 1rem;
}

.ai-form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
}

.ai-form-full {
    grid-column: 1 / -1;
}

.badge-ai {
    background: #eef2ff;
    color: #3730a3;
    border: 1px solid #c7d2fe;
    padding: 0.25rem 0.55rem;
    border-radius: 999px;
    font-size: 0.85rem;
}

.severity {
    padding: 0.25rem 0.55rem;
    border-radius: 999px;
    font-size: 0.85rem;
    text-transform: capitalize;
    border: 1px solid transparent;
}

.severity-info {
    background: #f3f4f6;
    color: #374151;
    border-color: #e5e7eb;
}

.severity-low {
    background: #ecfdf5;
    color: #047857;
    border-color: #bbf7d0;
}

.severity-medium {
    background: #fffbeb;
    color: #b45309;
    border-color: #fde68a;
}

.severity-high {
    background: #fef2f2;
    color: #b91c1c;
    border-color: #fecaca;
}

@media (max-width: 768px) {
    .ai-form-grid {
        grid-template-columns: 1fr;
    }
}
"""
    css_path.write_text(css_text, encoding="utf-8")
    print("Updated: app/static/css/styles.css")

print("")
print("DONE: Phase 5 AI Monitoring Event Logging files created.")
print("Next: run py_compile, restart server, and open /dashboard/ai-monitoring")
