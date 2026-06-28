from pathlib import Path

print("Applying Phase 2.1: Session Control UI...")

Path("app/routers/session_router.py").write_text(r'''from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.session_crud import create_session, get_session, get_sessions, update_session
from app.database.database import get_db
from app.models.classroom import Classroom
from app.models.class_session import ClassSession
from app.models.subject import Subject
from app.schemas.session_schema import ClassSessionCreate, ClassSessionRead, ClassSessionUpdate
from app.services.attendance_service import finalize_session_absences
from app.services.session_service import prepare_session_attendance

router = APIRouter(tags=["Class Sessions"])
templates = Jinja2Templates(directory="app/templates")


def close_other_active_sessions(db: Session, keep_session_id: int | None = None) -> None:
    """Keep teacher workflow simple: only one active session at a time."""
    query = db.query(ClassSession).filter(ClassSession.active.is_(True))
    if keep_session_id is not None:
        query = query.filter(ClassSession.id != keep_session_id)

    for session in query.all():
        session.active = False

    db.commit()


@router.get("/api/sessions", response_model=list[ClassSessionRead])
def api_list_sessions(db: Session = Depends(get_db)):
    return get_sessions(db)


@router.post("/api/sessions", response_model=ClassSessionRead)
def api_create_session(data: ClassSessionCreate, db: Session = Depends(get_db)):
    if data.active:
        close_other_active_sessions(db)

    session = create_session(db, data)
    prepare_session_attendance(db, session)
    return session


@router.get("/api/sessions/{session_id}", response_model=ClassSessionRead)
def api_get_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/api/sessions/{session_id}", response_model=ClassSessionRead)
def api_update_session(session_id: int, data: ClassSessionUpdate, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return update_session(db, session, data)


@router.post("/api/sessions/{session_id}/open", response_model=ClassSessionRead)
def api_open_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    close_other_active_sessions(db, keep_session_id=session.id)
    session.active = True
    db.commit()
    db.refresh(session)

    prepare_session_attendance(db, session)
    return session


@router.post("/api/sessions/{session_id}/close", response_model=ClassSessionRead)
def api_close_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return finalize_session_absences(db, session)


@router.get("/dashboard/sessions", response_class=HTMLResponse)
def dashboard_sessions(request: Request, db: Session = Depends(get_db)):
    active_session = (
        db.query(ClassSession)
        .filter(ClassSession.active.is_(True))
        .order_by(ClassSession.start_time.desc())
        .first()
    )

    return templates.TemplateResponse(
        request,
        "sessions/list.html",
        {
            "sessions": get_sessions(db),
            "classes": db.query(Classroom).order_by(Classroom.id).all(),
            "subjects": db.query(Subject).order_by(Subject.id).all(),
            "active_session": active_session,
        },
    )


@router.post("/dashboard/sessions/create")
def dashboard_create_session(
    classroom_id: int = Form(...),
    subject_id: int = Form(...),
    title: str = Form(...),
    db: Session = Depends(get_db),
):
    close_other_active_sessions(db)

    now = datetime.now().replace(microsecond=0)
    session = create_session(
        db,
        ClassSessionCreate(
            classroom_id=classroom_id,
            subject_id=subject_id,
            title=title,
            start_time=now,
            late_time=now + timedelta(minutes=15),
            close_time=now + timedelta(hours=2),
            active=True,
            created_by=1,
        ),
    )
    prepare_session_attendance(db, session)
    return RedirectResponse(url=f"/dashboard/sessions/{session.id}/attendance", status_code=303)


@router.post("/dashboard/sessions/{session_id}/open")
def dashboard_open_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    close_other_active_sessions(db, keep_session_id=session.id)
    session.active = True
    db.commit()
    db.refresh(session)

    prepare_session_attendance(db, session)
    return RedirectResponse(url="/dashboard/sessions", status_code=303)


@router.post("/dashboard/sessions/{session_id}/close")
def dashboard_close_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    finalize_session_absences(db, session)
    return RedirectResponse(url="/dashboard/sessions", status_code=303)
''', encoding="utf-8")


Path("app/templates/dashboard.html").write_text(r'''{% extends "base.html" %}
{% block content %}
<section class="page-header">
    <div>
        <p class="eyebrow">Phase 2.1 Teacher Workflow</p>
        <h1>Teacher Dashboard</h1>
        <p class="muted">QR attendance, manual override, and session control are ready.</p>
    </div>
    <a class="button secondary-button" href="/dashboard/sessions">Manage Sessions</a>
</section>

<section class="cards">
    <div class="card"><span>Total Students</span><strong>{{ stats.total_students }}</strong></div>
    <div class="card success"><span>Present</span><strong>{{ stats.present }}</strong></div>
    <div class="card warning"><span>Late</span><strong>{{ stats.late }}</strong></div>
    <div class="card danger"><span>Absent</span><strong>{{ stats.absent }}</strong></div>
    <div class="card info"><span>Permission</span><strong>{{ stats.permission }}</strong></div>
</section>

<section class="panel-grid">
    <div class="panel">
        <div class="panel-title-row">
            <h2>Active Session</h2>
            {% if stats.active_session %}
                <span class="badge-soft active-badge">Active</span>
            {% endif %}
        </div>

        {% if stats.active_session %}
            <p><strong>{{ stats.active_session.title }}</strong></p>
            <p class="muted">Start: {{ stats.active_session.start_time }}</p>
            <p class="muted">Late after: {{ stats.active_session.late_time }}</p>
            <p class="muted">Close: {{ stats.active_session.close_time }}</p>

            <div class="action-row">
                <a class="button" href="/dashboard/sessions/{{ stats.active_session.id }}/attendance">Open Attendance</a>
                <form action="/dashboard/sessions/{{ stats.active_session.id }}/close" method="post">
                    <button class="danger-button" type="submit">Close Session</button>
                </form>
            </div>
        {% else %}
            <p>No active session yet.</p>
            <a class="button" href="/dashboard/sessions">Create Session</a>
        {% endif %}
    </div>

    <div class="panel">
        <h2>System Status</h2>
        <ul class="status-list">
            <li><span class="dot ok"></span> FastAPI Backend Ready</li>
            <li><span class="dot ok"></span> SQLite Database Ready</li>
            <li><span class="dot ok"></span> QR Attendance Ready</li>
            <li><span class="dot muted-dot"></span> Face Recognition Later</li>
            <li><span class="dot muted-dot"></span> IoT Automation Later</li>
        </ul>
    </div>
</section>
{% endblock %}
''', encoding="utf-8")


Path("app/templates/sessions/list.html").write_text(r'''{% extends "base.html" %}
{% block content %}
<section class="page-header">
    <div>
        <p class="eyebrow">Class Session Management</p>
        <h1>Sessions</h1>
        <p class="muted">Create, open, close, and manage attendance sessions without PowerShell.</p>
    </div>
    <a class="button secondary-button" href="/dashboard">Back Dashboard</a>
</section>

{% if active_session %}
<section class="panel active-session-banner">
    <div>
        <p class="eyebrow">Current Active Session</p>
        <h2>{{ active_session.title }}</h2>
        <p class="muted">Start: {{ active_session.start_time }} | Late: {{ active_session.late_time }} | Close: {{ active_session.close_time }}</p>
    </div>
    <div class="action-row">
        <a class="button" href="/dashboard/sessions/{{ active_session.id }}/attendance">Open Attendance</a>
        <form action="/dashboard/sessions/{{ active_session.id }}/close" method="post">
            <button class="danger-button" type="submit">Close Session</button>
        </form>
    </div>
</section>
{% endif %}

<form class="form-card" action="/dashboard/sessions/create" method="post">
    <h2>Create New Live Session</h2>
    <div class="form-row">
        <select name="classroom_id" required>
            {% for c in classes %}<option value="{{ c.id }}">{{ c.code }} - {{ c.name }}</option>{% endfor %}
        </select>
        <select name="subject_id" required>
            {% for s in subjects %}<option value="{{ s.id }}">{{ s.code }} - {{ s.name }}</option>{% endfor %}
        </select>
        <input name="title" placeholder="Session title" value="Live QR Attendance Test" required>
        <button type="submit">Create & Open</button>
    </div>
    <p class="muted">This creates a session starting now, late after 15 minutes, close after 2 hours. Other active sessions will be closed automatically.</p>
</form>

<section class="panel">
    <h2>Session List</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Start</th>
                <th>Late Time</th>
                <th>Close</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
        {% for session in sessions %}
            <tr class="{% if session.active %}active-row{% endif %}">
                <td>{{ session.id }}</td>
                <td>
                    <strong>{{ session.title }}</strong>
                    {% if session.active %}<span class="badge-soft active-badge">Current</span>{% endif %}
                </td>
                <td>{{ session.start_time }}</td>
                <td>{{ session.late_time }}</td>
                <td>{{ session.close_time }}</td>
                <td>
                    {% if session.active %}
                        <span class="badge-soft active-badge">Active</span>
                    {% else %}
                        <span class="badge-soft closed-badge">Closed</span>
                    {% endif %}
                </td>
                <td>
                    <div class="table-actions">
                        <a class="button small-button" href="/dashboard/sessions/{{ session.id }}/attendance">Attendance</a>

                        {% if session.active %}
                            <form action="/dashboard/sessions/{{ session.id }}/close" method="post">
                                <button class="danger-button small-button" type="submit">Close</button>
                            </form>
                        {% else %}
                            <form action="/dashboard/sessions/{{ session.id }}/open" method="post">
                                <button class="secondary-button small-button" type="submit">Open</button>
                            </form>
                        {% endif %}
                    </div>
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</section>
{% endblock %}
''', encoding="utf-8")


Path("app/templates/attendance/detail.html").write_text(r'''{% extends "base.html" %}
{% block content %}
<section class="page-header">
    <div>
        <p class="eyebrow">Phase 2 Attendance</p>
        <h1>{{ session.title }}</h1>
        <p class="muted">QR scans create attendance events and update final records per session.</p>
    </div>

    <div class="action-row">
        {% if session.active %}
            <span class="badge-soft active-badge">Active Session</span>
            <form action="/dashboard/sessions/{{ session.id }}/close" method="post">
                <button class="danger-button" type="submit">Close Session</button>
            </form>
        {% else %}
            <span class="badge-soft closed-badge">Closed Session</span>
            <form action="/dashboard/sessions/{{ session.id }}/open" method="post">
                <button class="secondary-button" type="submit">Reopen Session</button>
            </form>
        {% endif %}
        <a class="button secondary-button" href="/dashboard/sessions">Back Sessions</a>
    </div>
</section>

<section class="session-info-grid">
    <div class="mini-card"><span>Start</span><strong>{{ session.start_time }}</strong></div>
    <div class="mini-card"><span>Late After</span><strong>{{ session.late_time }}</strong></div>
    <div class="mini-card"><span>Close Time</span><strong>{{ session.close_time }}</strong></div>
</section>

{% if scan_message %}
<section class="alert alert-{{ scan_result }}">
    <strong>Scan result:</strong> {{ scan_message }}
</section>
{% endif %}

<section class="panel scan-panel">
    <h2>QR Attendance Scan</h2>

    {% if session.active %}
        <form class="form-row" action="/dashboard/attendance/scan-qr" method="post">
            <input type="hidden" name="session_id" value="{{ session.id }}">
            <input name="qr_code" placeholder="Paste or scan QR value, e.g. SC-STUDENT-S001" required autofocus>
            <button type="submit">Scan QR</button>
        </form>

        <div class="quick-scan-list">
            <span class="muted">Quick demo scan:</span>
            {% for qr in ["SC-STUDENT-S001", "SC-STUDENT-S002", "SC-STUDENT-S003", "SC-STUDENT-S004", "SC-STUDENT-S005"] %}
                <form action="/dashboard/attendance/scan-qr" method="post">
                    <input type="hidden" name="session_id" value="{{ session.id }}">
                    <input type="hidden" name="qr_code" value="{{ qr }}">
                    <button class="qr-chip" type="submit">{{ qr }}</button>
                </form>
            {% endfor %}
        </div>
    {% else %}
        <p class="muted">This session is closed. Reopen it first if you need to test more QR scans.</p>
    {% endif %}
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


css_path = Path("app/static/css/styles.css")
css = css_path.read_text(encoding="utf-8")

phase21_css = r'''

/* Phase 2.1 Teacher session control UI */
.panel-title-row,
.action-row,
.table-actions,
.quick-scan-list {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.panel-title-row {
    justify-content: space-between;
}

.secondary-button {
    background: #e2e8f0 !important;
    color: #0f172a !important;
}

.danger-button {
    background: var(--danger) !important;
    color: #ffffff !important;
}

.small-button {
    padding: 7px 10px !important;
    border-radius: 9px !important;
    font-size: 13px !important;
}

.badge-soft {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
}

.active-badge {
    background: #dcfce7;
    color: #166534;
}

.closed-badge {
    background: #e2e8f0;
    color: #475569;
}

.active-session-banner {
    border-left: 5px solid var(--success);
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    gap: 14px;
    align-items: center;
    flex-wrap: wrap;
}

.active-row {
    background: #f0fdf4;
}

.session-info-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(160px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
}

.mini-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 14px;
}

.mini-card span {
    display: block;
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 6px;
}

.mini-card strong {
    font-size: 14px;
}

.quick-scan-list {
    margin-top: 14px;
}

.qr-chip {
    background: #f1f5f9 !important;
    color: #334155 !important;
    border: 1px solid #cbd5e1 !important;
    font-size: 12px !important;
    padding: 7px 9px !important;
}

.qr-chip:hover {
    background: #dbeafe !important;
    color: #1d4ed8 !important;
}

@media (max-width: 900px) {
    .session-info-grid {
        grid-template-columns: 1fr;
    }
}
'''

if "/* Phase 2.1 Teacher session control UI */" not in css:
    css_path.write_text(css + phase21_css, encoding="utf-8")

print("DONE: Phase 2.1 updated successfully.")
print("Changed files:")
print("- app/routers/session_router.py")
print("- app/templates/dashboard.html")
print("- app/templates/sessions/list.html")
print("- app/templates/attendance/detail.html")
print("- app/static/css/styles.css")
