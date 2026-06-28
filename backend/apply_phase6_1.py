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

write_file("app/models/iot_automation_event.py", r"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class IoTAutomationEvent(Base):
    __tablename__ = "iot_automation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_name: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="skipped")
    occupancy_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
""")

write_file("app/services/iot_automation_service.py", r"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.attendance_record import AttendanceRecord
from app.models.class_session import ClassSession
from app.models.device import Device
from app.models.iot_automation_event import IoTAutomationEvent


OCCUPIED_STATUSES = ["P", "L", "Pm"]


def get_active_session(db: Session):
    return (
        db.query(ClassSession)
        .filter(ClassSession.active == True)
        .order_by(ClassSession.start_time.desc())
        .first()
    )


def get_current_occupancy_count(db: Session):
    active_session = get_active_session(db)
    if not active_session:
        return 0, None

    count = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == active_session.id)
        .filter(AttendanceRecord.status.in_(OCCUPIED_STATUSES))
        .count()
    )

    return count, active_session


def list_automation_events(db: Session, limit: int = 30):
    return (
        db.query(IoTAutomationEvent)
        .order_by(IoTAutomationEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def create_automation_event(
    db: Session,
    rule_name: str,
    action: str,
    status: str,
    occupancy_count: int,
    reason: str,
):
    event = IoTAutomationEvent(
        rule_name=rule_name,
        action=action,
        status=status,
        occupancy_count=occupancy_count,
        reason=reason,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def turn_off_light_and_fan(db: Session):
    devices = (
        db.query(Device)
        .filter(Device.type.in_(["light", "fan"]))
        .all()
    )

    affected = []
    for device in devices:
        if device.status != "off":
            device.status = "off"
            device.last_seen = datetime.utcnow()
            affected.append(device.name)

    db.commit()
    return affected


def evaluate_auto_off_rule(db: Session, simulate_empty: bool = False):
    occupancy_count, active_session = get_current_occupancy_count(db)

    rule_name = "auto_light_fan_off_after_5_min_empty"
    action = "turn_off_light_and_fan"

    if simulate_empty:
        occupancy_count = 0
        affected = turn_off_light_and_fan(db)
        reason = (
            "Demo simulation: classroom treated as empty for 5 minutes. "
            f"Turned off: {', '.join(affected) if affected else 'already off'}."
        )
        event = create_automation_event(
            db=db,
            rule_name=rule_name,
            action=action,
            status="executed",
            occupancy_count=occupancy_count,
            reason=reason,
        )
        return {
            "success": True,
            "executed": True,
            "occupancy_count": occupancy_count,
            "active_session_id": active_session.id if active_session else None,
            "affected_devices": affected,
            "message": reason,
            "event_id": event.id,
        }

    if occupancy_count > 0:
        reason = (
            f"Automation skipped because {occupancy_count} student(s) are currently marked present/late/permission "
            "in the active session."
        )
        event = create_automation_event(
            db=db,
            rule_name=rule_name,
            action=action,
            status="skipped",
            occupancy_count=occupancy_count,
            reason=reason,
        )
        return {
            "success": True,
            "executed": False,
            "occupancy_count": occupancy_count,
            "active_session_id": active_session.id if active_session else None,
            "affected_devices": [],
            "message": reason,
            "event_id": event.id,
        }

    affected = turn_off_light_and_fan(db)
    reason = (
        "No occupied students found in active session. "
        f"Turned off: {', '.join(affected) if affected else 'already off'}."
    )
    event = create_automation_event(
        db=db,
        rule_name=rule_name,
        action=action,
        status="executed",
        occupancy_count=occupancy_count,
        reason=reason,
    )
    return {
        "success": True,
        "executed": True,
        "occupancy_count": occupancy_count,
        "active_session_id": active_session.id if active_session else None,
        "affected_devices": affected,
        "message": reason,
        "event_id": event.id,
    }
""")

# Update models __init__
models_init = read_file("app/models/__init__.py")
if "iot_automation_event" not in models_init:
    models_init += "\nfrom app.models.iot_automation_event import IoTAutomationEvent\n"
    save_file("app/models/__init__.py", models_init)

# Patch IoT router
iot_router = read_file("app/routers/iot_router.py")

if "iot_automation_service" not in iot_router:
    iot_router = iot_router.replace(
        "from app.services.iot_service import (",
        "from app.services.iot_automation_service import evaluate_auto_off_rule, list_automation_events\nfrom app.services.iot_service import (",
    )

if 'automation_events = list_automation_events(db, limit=30)' not in iot_router:
    iot_router = iot_router.replace(
        "stats = get_iot_stats(db)\n\n    return templates.TemplateResponse(",
        "stats = get_iot_stats(db)\n    automation_events = list_automation_events(db, limit=30)\n\n    return templates.TemplateResponse(",
    )

    iot_router = iot_router.replace(
        '"stats": stats,\n        },',
        '"stats": stats,\n            "automation_events": automation_events,\n        },',
    )

if '@router.post("/api/iot/automation/check-auto-off")' not in iot_router:
    iot_router += r'''


@router.post("/api/iot/automation/check-auto-off")
def api_check_auto_off_rule(db: Session = Depends(get_db)):
    return evaluate_auto_off_rule(db, simulate_empty=False)


@router.post("/api/iot/automation/simulate-empty-auto-off")
def api_simulate_empty_auto_off(db: Session = Depends(get_db)):
    return evaluate_auto_off_rule(db, simulate_empty=True)


@router.post("/dashboard/iot-monitoring/check-auto-off")
def dashboard_check_auto_off_rule(db: Session = Depends(get_db)):
    evaluate_auto_off_rule(db, simulate_empty=False)
    return RedirectResponse(url="/dashboard/iot-monitoring", status_code=303)


@router.post("/dashboard/iot-monitoring/simulate-empty-auto-off")
def dashboard_simulate_empty_auto_off(db: Session = Depends(get_db)):
    evaluate_auto_off_rule(db, simulate_empty=True)
    return RedirectResponse(url="/dashboard/iot-monitoring", status_code=303)
'''
    save_file("app/routers/iot_router.py", iot_router)

# Patch IoT template
template = read_file("app/templates/iot_monitoring/index.html")

if "Phase 6.1 Automation Rule Controls" not in template:
    automation_block = r'''
<!-- Phase 6.1 Automation Rule Controls -->
<div class="card">
    <h2>Automation Rule: Empty Classroom Auto-Off</h2>
    <p class="muted">
        Teacher requirement: if no students are detected in the classroom for 5 minutes,
        the system can automatically turn off lights and fans.
    </p>

    <div class="quick-ai-grid">
        <form method="post" action="/dashboard/iot-monitoring/check-auto-off">
            <button class="btn btn-warning" type="submit">Check Auto-Off Rule</button>
        </form>

        <form method="post" action="/dashboard/iot-monitoring/simulate-empty-auto-off">
            <button class="btn btn-danger" type="submit">Simulate Empty Classroom Auto-Off</button>
        </form>
    </div>
</div>

<div class="card">
    <h2>Automation Event History</h2>

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
                    <td colspan="6" class="muted">No automation events yet.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
'''

    template = template.replace(
        '<div class="card">\n    <h2>Automation Foundation</h2>',
        automation_block + '\n<div class="card">\n    <h2>Automation Foundation</h2>',
    )
    save_file("app/templates/iot_monitoring/index.html", template)

# Patch CSS
css = read_file("app/static/css/styles.css")

if "Phase 6.1 IoT Automation Rules" not in css:
    css += r"""

/* Phase 6.1 IoT Automation Rules */
.automation-status {
    display: inline-block;
    padding: 0.25rem 0.55rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: capitalize;
    border: 1px solid #e5e7eb;
}

.automation-status-executed {
    background: #ecfdf5;
    border-color: #bbf7d0;
    color: #047857;
}

.automation-status-skipped {
    background: #fffbeb;
    border-color: #fde68a;
    color: #b45309;
}
"""
    save_file("app/static/css/styles.css", css)

print("")
print("DONE: Phase 6.1 IoT Automation Rules applied.")
