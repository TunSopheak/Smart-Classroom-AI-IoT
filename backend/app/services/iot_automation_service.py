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
