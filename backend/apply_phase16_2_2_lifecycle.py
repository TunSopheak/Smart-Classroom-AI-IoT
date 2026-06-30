from pathlib import Path
import re

ROOT = Path(".")
BACKEND = ROOT / "backend"

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")
    print(f"Updated: {path}")

# 1) Patch ClassSession model with archived column
class_session_path = BACKEND / "app/models/class_session.py"
class_session = read(class_session_path)

if "archived" not in class_session:
    if "Boolean" not in class_session.split("\n")[0:10]:
        class_session = class_session.replace("Column,", "Column, Boolean,", 1)

    insert_after = None
    for candidate in [
        "active = Column(Boolean, default=True)",
        "active = Column(Boolean, default=True, nullable=False)",
    ]:
        if candidate in class_session:
            insert_after = candidate
            break

    if insert_after:
        class_session = class_session.replace(
            insert_after,
            insert_after + "\n    archived = Column(Boolean, default=False, nullable=False)",
            1,
        )
    else:
        class_session = class_session.replace(
            "class ClassSession",
            "class ClassSession",
            1,
        )
        class_session = class_session.replace(
            "\n    created_at",
            "\n    archived = Column(Boolean, default=False, nullable=False)\n    created_at",
            1,
        )

write(class_session_path, class_session)

# 2) Add safe migration for archived column
migration_path = BACKEND / "app/database/migrations.py"
migrations = read(migration_path) if migration_path.exists() else ""

migration_patch = r'''

# Phase 16.2.2 safe migration: archived sessions
def ensure_session_archived_column(engine):
    with engine.connect() as connection:
        columns = connection.exec_driver_sql("PRAGMA table_info(class_sessions)").fetchall()
        column_names = {column[1] for column in columns}

        if "archived" not in column_names:
            connection.exec_driver_sql(
                "ALTER TABLE class_sessions ADD COLUMN archived BOOLEAN NOT NULL DEFAULT 0"
            )
            connection.commit()
'''

if "ensure_session_archived_column" not in migrations:
    migrations += migration_patch
    write(migration_path, migrations)

# 3) Call migration from main.py
main_path = BACKEND / "app/main.py"
main = read(main_path)

if "ensure_session_archived_column" not in main:
    main += r'''

# Phase 16.2.2 migration bootstrap
try:
    from app.database.database import engine
    from app.database.migrations import ensure_session_archived_column
    ensure_session_archived_column(engine)
except Exception as migration_error:
    print("Phase 16.2.2 migration warning:", migration_error)
'''
    write(main_path, main)

# 4) Add academic lifecycle router
router_path = BACKEND / "app/routers/academic_lifecycle_router.py"
router = r'''
from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.academic import ClassGroup, Course, StudentEnrollment, WeeklySchedule
from app.models.class_session import ClassSession


router = APIRouter(tags=["Academic Lifecycle"])


def redirect_class_setup(message: str = ""):
    url = "/dashboard/class-setup"
    if message:
        url += f"?message={message}"
    return RedirectResponse(url=url, status_code=303)


def redirect_sessions(message: str = ""):
    url = "/dashboard/sessions"
    if message:
        url += f"?message={message}"
    return RedirectResponse(url=url, status_code=303)


@router.post("/dashboard/class-setup/class-groups/{group_id}/update")
def update_class_group(
    group_id: int,
    code: str = Form(...),
    name: str = Form(...),
    academic_year: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    group = db.query(ClassGroup).filter(ClassGroup.id == group_id).first()

    if not group:
        return redirect_class_setup("Class group not found")

    normalized_code = code.strip().upper()

    duplicate = (
        db.query(ClassGroup)
        .filter(ClassGroup.code == normalized_code)
        .filter(ClassGroup.id != group_id)
        .first()
    )

    if duplicate:
        return redirect_class_setup("Class group code already exists")

    group.code = normalized_code
    group.name = name.strip()
    group.academic_year = academic_year.strip() or None
    group.description = description.strip() or None
    group.active = True

    db.commit()
    return redirect_class_setup("Class group updated")


@router.post("/dashboard/class-setup/class-groups/{group_id}/deactivate")
def deactivate_class_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(ClassGroup).filter(ClassGroup.id == group_id).first()

    if not group:
        return redirect_class_setup("Class group not found")

    active_session = (
        db.query(ClassSession)
        .filter(ClassSession.class_group_id == group.id)
        .filter(ClassSession.active == True)
        .first()
    )

    if active_session:
        return redirect_class_setup("Cannot deactivate class group while it has an active session")

    group.active = False
    db.commit()
    return redirect_class_setup("Class group deactivated")


@router.post("/dashboard/class-setup/courses/{course_id}/update")
def update_course(
    course_id: int,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        return redirect_class_setup("Course not found")

    normalized_code = code.strip().upper()

    duplicate = (
        db.query(Course)
        .filter(Course.code == normalized_code)
        .filter(Course.id != course_id)
        .first()
    )

    if duplicate:
        return redirect_class_setup("Course code already exists")

    course.code = normalized_code
    course.name = name.strip()
    course.description = description.strip() or None
    course.active = True

    db.commit()
    return redirect_class_setup("Course updated")


@router.post("/dashboard/class-setup/courses/{course_id}/deactivate")
def deactivate_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        return redirect_class_setup("Course not found")

    active_session = (
        db.query(ClassSession)
        .filter(ClassSession.course_id == course.id)
        .filter(ClassSession.active == True)
        .first()
    )

    if active_session:
        return redirect_class_setup("Cannot deactivate course while it has an active session")

    course.active = False
    db.commit()
    return redirect_class_setup("Course deactivated")


@router.post("/dashboard/class-setup/schedules/{schedule_id}/update")
def update_weekly_schedule(
    schedule_id: int,
    class_group_id: int = Form(...),
    course_id: int = Form(...),
    weekday: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    late_after_minutes: int = Form(15),
    location: str = Form(""),
    db: Session = Depends(get_db),
):
    schedule = db.query(WeeklySchedule).filter(WeeklySchedule.id == schedule_id).first()

    if not schedule:
        return redirect_class_setup("Schedule not found")

    duplicate = (
        db.query(WeeklySchedule)
        .filter(WeeklySchedule.id != schedule_id)
        .filter(WeeklySchedule.class_group_id == class_group_id)
        .filter(WeeklySchedule.course_id == course_id)
        .filter(WeeklySchedule.weekday == weekday)
        .filter(WeeklySchedule.start_time == start_time)
        .filter(WeeklySchedule.end_time == end_time)
        .first()
    )

    if duplicate:
        return redirect_class_setup("A similar weekly schedule already exists")

    schedule.class_group_id = class_group_id
    schedule.course_id = course_id
    schedule.weekday = weekday
    schedule.start_time = start_time
    schedule.end_time = end_time
    schedule.late_after_minutes = late_after_minutes
    schedule.location = location.strip() or None
    schedule.active = True

    db.commit()
    return redirect_class_setup("Weekly schedule updated. Existing sessions keep their original history")


@router.post("/dashboard/class-setup/schedules/{schedule_id}/deactivate")
def deactivate_weekly_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(WeeklySchedule).filter(WeeklySchedule.id == schedule_id).first()

    if not schedule:
        return redirect_class_setup("Schedule not found")

    schedule.active = False
    db.commit()
    return redirect_class_setup("Weekly schedule deactivated. Existing sessions are not changed")


@router.post("/dashboard/class-setup/enrollments/{enrollment_id}/deactivate")
def deactivate_enrollment(enrollment_id: int, db: Session = Depends(get_db)):
    enrollment = db.query(StudentEnrollment).filter(StudentEnrollment.id == enrollment_id).first()

    if not enrollment:
        return redirect_class_setup("Enrollment not found")

    enrollment.active = False
    db.commit()
    return redirect_class_setup("Student removed from class group")


@router.post("/dashboard/sessions/{session_id}/archive")
def archive_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ClassSession).filter(ClassSession.id == session_id).first()

    if not session:
        return redirect_sessions("Session not found")

    if session.active:
        return redirect_sessions("Close the session before archiving it")

    session.archived = True
    db.commit()

    return redirect_sessions("Session archived")
'''
write(router_path, router)

# 5) Include router in main.py
main = read(main_path)
if "academic_lifecycle_router" not in main:
    main += r'''

# Phase 16.2.2 Academic lifecycle routes
from app.routers.academic_lifecycle_router import router as academic_lifecycle_router
app.include_router(academic_lifecycle_router)
'''
    write(main_path, main)

# 6) Hide archived sessions from common session queries if possible
session_router_path = BACKEND / "app/routers/session_router.py"
session_router = read(session_router_path)

if "ClassSession.archived == False" not in session_router and "ClassSession" in session_router:
    session_router = session_router.replace(
        "db.query(ClassSession).order_by(",
        "db.query(ClassSession).filter(ClassSession.archived == False).order_by(",
    )
    session_router = session_router.replace(
        "db.query(ClassSession).filter(ClassSession.active == True)",
        "db.query(ClassSession).filter(ClassSession.active == True).filter(ClassSession.archived == False)",
    )
    write(session_router_path, session_router)

# 7) Add lifecycle management section to class setup page
class_setup_path = BACKEND / "app/templates/class_setup/index.html"
tpl = read(class_setup_path)

lifecycle_section = r'''

<section class="card lifecycle-management-card">
    <div class="section-title-row">
        <div>
            <h2>Lifecycle Management</h2>
            <p class="muted">Edit or deactivate academic setup data safely. Existing history is preserved for reports.</p>
        </div>
    </div>

    {% if request.query_params.get("message") %}
    <div class="success-note compact-note">{{ request.query_params.get("message") }}</div>
    {% endif %}

    <div class="lifecycle-grid">
        <div class="lifecycle-panel">
            <h3>Class Groups</h3>
            {% for group in class_groups|default([]) %}
            <form method="post" action="/dashboard/class-setup/class-groups/{{ group.id }}/update" class="lifecycle-row">
                <input name="code" value="{{ group.code }}" required>
                <input name="name" value="{{ group.name }}" required>
                <input name="academic_year" value="{{ group.academic_year or '' }}" placeholder="Academic year">
                <input name="description" value="{{ group.description or '' }}" placeholder="Description">
                <button class="btn btn-primary btn-sm" type="submit">Save</button>
            </form>
            <form method="post" action="/dashboard/class-setup/class-groups/{{ group.id }}/deactivate" class="lifecycle-danger-form">
                <button class="btn btn-secondary btn-sm" type="submit">Deactivate {{ group.code }}</button>
            </form>
            {% else %}
            <p class="muted">No class groups yet.</p>
            {% endfor %}
        </div>

        <div class="lifecycle-panel">
            <h3>Courses</h3>
            {% for course in courses|default([]) %}
            <form method="post" action="/dashboard/class-setup/courses/{{ course.id }}/update" class="lifecycle-row">
                <input name="code" value="{{ course.code }}" required>
                <input name="name" value="{{ course.name }}" required>
                <input name="description" value="{{ course.description or '' }}" placeholder="Description">
                <button class="btn btn-primary btn-sm" type="submit">Save</button>
            </form>
            <form method="post" action="/dashboard/class-setup/courses/{{ course.id }}/deactivate" class="lifecycle-danger-form">
                <button class="btn btn-secondary btn-sm" type="submit">Deactivate {{ course.code }}</button>
            </form>
            {% else %}
            <p class="muted">No courses yet.</p>
            {% endfor %}
        </div>
    </div>

    <div class="lifecycle-panel lifecycle-schedules">
        <h3>Weekly Schedules</h3>

        {% set schedule_list = weekly_schedules|default(schedules|default([])) %}

        {% for schedule in schedule_list %}
        <form method="post" action="/dashboard/class-setup/schedules/{{ schedule.id }}/update" class="lifecycle-schedule-row">
            <select name="class_group_id" required>
                {% for group in class_groups|default([]) %}
                <option value="{{ group.id }}" {% if group.id == schedule.class_group_id %}selected{% endif %}>
                    {{ group.code }}
                </option>
                {% endfor %}
            </select>

            <select name="course_id" required>
                {% for course in courses|default([]) %}
                <option value="{{ course.id }}" {% if course.id == schedule.course_id %}selected{% endif %}>
                    {{ course.code }}
                </option>
                {% endfor %}
            </select>

            <select name="weekday">
                {% for value, label in [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")] %}
                <option value="{{ value }}" {% if value == schedule.weekday %}selected{% endif %}>{{ label }}</option>
                {% endfor %}
            </select>

            <input name="start_time" value="{{ schedule.start_time }}" required>
            <input name="end_time" value="{{ schedule.end_time }}" required>
            <input name="late_after_minutes" type="number" min="0" value="{{ schedule.late_after_minutes or 15 }}">
            <input name="location" value="{{ schedule.location or '' }}" placeholder="Location">

            <button class="btn btn-primary btn-sm" type="submit">Save</button>
        </form>

        <form method="post" action="/dashboard/class-setup/schedules/{{ schedule.id }}/deactivate" class="lifecycle-danger-form">
            <button class="btn btn-secondary btn-sm" type="submit">Deactivate Schedule</button>
        </form>
        {% else %}
        <p class="muted">No weekly schedules yet.</p>
        {% endfor %}
    </div>
</section>
'''

if "Lifecycle Management" not in tpl:
    if "{% endblock %}" in tpl:
        tpl = tpl.replace("{% endblock %}", lifecycle_section + "\n{% endblock %}", 1)
    else:
        tpl += lifecycle_section
    write(class_setup_path, tpl)

# 8) Add archive section to sessions page
sessions_path = BACKEND / "app/templates/sessions/list.html"
sessions_tpl = read(sessions_path)

archive_section = r'''

<section class="card lifecycle-management-card">
    <div class="section-title-row">
        <div>
            <h2>Session Lifecycle</h2>
            <p class="muted">Archive closed sessions to hide them from daily lists while preserving attendance/report history.</p>
        </div>
    </div>

    {% if request.query_params.get("message") %}
    <div class="success-note compact-note">{{ request.query_params.get("message") }}</div>
    {% endif %}

    <div class="table-responsive">
        <table class="data-table compact-data-table">
            <thead>
                <tr>
                    <th>Session</th>
                    <th>Status</th>
                    <th>Archive</th>
                </tr>
            </thead>
            <tbody>
                {% for session in sessions|default([]) %}
                {% if not session.active and not session.archived %}
                <tr>
                    <td>
                        <strong>#{{ session.id }} - {{ session.title }}</strong>
                    </td>
                    <td><span class="badge muted-badge">Closed</span></td>
                    <td>
                        <form method="post" action="/dashboard/sessions/{{ session.id }}/archive">
                            <button class="btn btn-secondary btn-sm" type="submit">Archive</button>
                        </form>
                    </td>
                </tr>
                {% endif %}
                {% else %}
                <tr>
                    <td colspan="3" class="muted">No closed sessions available for archiving.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</section>
'''

if "Session Lifecycle" not in sessions_tpl:
    if "{% endblock %}" in sessions_tpl:
        sessions_tpl = sessions_tpl.replace("{% endblock %}", archive_section + "\n{% endblock %}", 1)
    else:
        sessions_tpl += archive_section
    write(sessions_path, sessions_tpl)

# 9) CSS polish
css_path = BACKEND / "app/static/css/styles.css"
css = read(css_path)

if "Phase 16.2.2 lifecycle management UI" not in css:
    css += r'''

/* Phase 16.2.2 lifecycle management UI */
.lifecycle-management-card {
    margin-top: 1rem;
}

.lifecycle-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
}

.lifecycle-panel {
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 1rem;
    background: #f8fafc;
    min-width: 0;
}

.lifecycle-panel h3 {
    margin-bottom: 0.85rem;
    font-size: 1rem !important;
}

.lifecycle-row,
.lifecycle-schedule-row {
    display: grid;
    gap: 0.55rem;
    margin-bottom: 0.55rem;
}

.lifecycle-row {
    grid-template-columns: 0.85fr 1.35fr 0.85fr 1.1fr auto;
}

.lifecycle-schedule-row {
    grid-template-columns: 1fr 0.8fr 0.95fr 0.75fr 0.75fr 0.6fr 1fr auto;
}

.lifecycle-row input,
.lifecycle-row select,
.lifecycle-schedule-row input,
.lifecycle-schedule-row select {
    min-width: 0;
    height: 38px;
    font-size: 0.88rem !important;
}

.lifecycle-danger-form {
    margin: 0 0 0.9rem;
}

.compact-note {
    margin: 0.75rem 0 1rem;
    padding: 0.75rem 0.9rem !important;
}

.muted-badge {
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #475569;
}

.compact-data-table td,
.compact-data-table th {
    font-size: 0.88rem !important;
}

@media (max-width: 1200px) {
    .lifecycle-grid {
        grid-template-columns: 1fr;
    }

    .lifecycle-row,
    .lifecycle-schedule-row {
        grid-template-columns: 1fr 1fr;
    }
}

@media (max-width: 700px) {
    .lifecycle-row,
    .lifecycle-schedule-row {
        grid-template-columns: 1fr;
    }
}
'''
    write(css_path, css)

# 10) Docs
doc_path = ROOT / "docs/academic_lifecycle_safe_rules.md"
doc = r'''# Phase 16.2.2 Academic Lifecycle Safe Rules

## Principle

Academic records should not be hard-deleted after they are connected to history.

## Rules

- Class Group: edit or deactivate. Do not hard delete if sessions/enrollments exist.
- Course: edit or deactivate. Do not hard delete if schedules/sessions exist.
- Weekly Schedule: edit affects future sessions only. Existing sessions keep their history.
- Session: closed sessions can be archived. Active sessions must be closed before archive.
- Student Enrollment: remove from class means deactivate enrollment, not delete student.

## Added Routes

```text
POST /dashboard/class-setup/class-groups/{group_id}/update
POST /dashboard/class-setup/class-groups/{group_id}/deactivate
POST /dashboard/class-setup/courses/{course_id}/update
POST /dashboard/class-setup/courses/{course_id}/deactivate
POST /dashboard/class-setup/schedules/{schedule_id}/update
POST /dashboard/class-setup/schedules/{schedule_id}/deactivate
POST /dashboard/class-setup/enrollments/{enrollment_id}/deactivate
POST /dashboard/sessions/{session_id}/archive
```
'''
write(doc_path, doc)

print("")
print("DONE: Phase 16.2.2 academic lifecycle patch applied.")
