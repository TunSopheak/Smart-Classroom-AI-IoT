from pathlib import Path
import re

ROOT = Path(".")
BACKEND = ROOT / "backend"

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, text):
    Path(path).write_text(text, encoding="utf-8")
    print(f"Updated: {path}")

# 1) Add academic rule service
rules_path = BACKEND / "app/services/academic_rules.py"
rules_code = r'''
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.academic import WeeklySchedule
from app.models.class_session import ClassSession


def normalize_time_value(value: str) -> str:
    raw = str(value or "").strip()

    if not raw:
        raise ValueError("Time is required")

    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(raw.upper(), fmt).strftime("%H:%M")
        except ValueError:
            pass

    raise ValueError(f"Invalid time format: {raw}")


def time_to_minutes(value: str) -> int:
    normalized = normalize_time_value(value)
    hour, minute = normalized.split(":")
    return int(hour) * 60 + int(minute)


def times_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    a_start = time_to_minutes(start_a)
    a_end = time_to_minutes(end_a)
    b_start = time_to_minutes(start_b)
    b_end = time_to_minutes(end_b)

    return max(a_start, b_start) < min(a_end, b_end)


def validate_weekly_schedule_rule(
    db: Session,
    class_group_id: int,
    course_id: int,
    weekday: int,
    start_time: str,
    end_time: str,
    exclude_schedule_id: Optional[int] = None,
) -> Tuple[bool, str, str, str]:
    try:
        normalized_start = normalize_time_value(start_time)
        normalized_end = normalize_time_value(end_time)
    except ValueError as exc:
        return False, str(exc), start_time, end_time

    if time_to_minutes(normalized_start) >= time_to_minutes(normalized_end):
        return False, "End time must be after start time", normalized_start, normalized_end

    query = (
        db.query(WeeklySchedule)
        .filter(WeeklySchedule.active == True)
        .filter(WeeklySchedule.class_group_id == class_group_id)
        .filter(WeeklySchedule.weekday == weekday)
    )

    if exclude_schedule_id is not None:
        query = query.filter(WeeklySchedule.id != exclude_schedule_id)

    schedules = query.all()

    for existing in schedules:
        existing_start = normalize_time_value(existing.start_time)
        existing_end = normalize_time_value(existing.end_time)

        if times_overlap(normalized_start, normalized_end, existing_start, existing_end):
            if existing.course_id == course_id and existing_start == normalized_start and existing_end == normalized_end:
                return (
                    False,
                    "Duplicate schedule: this class already has the same course at the same day and time",
                    normalized_start,
                    normalized_end,
                )

            return (
                False,
                f"Schedule conflict: this class already has another course from {existing_start} to {existing_end}",
                normalized_start,
                normalized_end,
            )

    return True, "OK", normalized_start, normalized_end


def class_has_active_session(
    db: Session,
    class_group_id: Optional[int],
    exclude_session_id: Optional[int] = None,
) -> Optional[ClassSession]:
    if not class_group_id:
        return None

    query = (
        db.query(ClassSession)
        .filter(ClassSession.class_group_id == class_group_id)
        .filter(ClassSession.active == True)
    )

    if hasattr(ClassSession, "archived"):
        query = query.filter(ClassSession.archived == False)

    if exclude_session_id is not None:
        query = query.filter(ClassSession.id != exclude_session_id)

    return query.first()
'''
write(rules_path, rules_code)

# 2) Patch class_setup_router schedule creation
class_setup_path = BACKEND / "app/routers/class_setup_router.py"
router = read(class_setup_path)

if "validate_weekly_schedule_rule" not in router:
    router = "from app.services.academic_rules import validate_weekly_schedule_rule, class_has_active_session\n" + router

# Insert validation before WeeklySchedule creation if missing
if "validate_weekly_schedule_rule(db, class_group_id" not in router:
    marker = "schedule = WeeklySchedule("
    if marker in router:
        validation = '''
    ok, message, normalized_start, normalized_end = validate_weekly_schedule_rule(
        db=db,
        class_group_id=class_group_id,
        course_id=course_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
    )

    if not ok:
        return RedirectResponse(
            url=f"/dashboard/class-setup?message={message}",
            status_code=303,
        )

    start_time = normalized_start
    end_time = normalized_end

'''
        router = router.replace(marker, validation + "    " + marker, 1)
    else:
        print("WARNING: Could not find WeeklySchedule creation marker in class_setup_router.py")

# Add active session guard before ClassSession from schedule if possible
if "This class already has an active session" not in router:
    marker2 = "session = ClassSession("
    if marker2 in router:
        active_guard = '''
    active_session = class_has_active_session(db, getattr(schedule, "class_group_id", None))
    if active_session:
        return RedirectResponse(
            url=f"/dashboard/class-setup?message=This class already has an active session #{active_session.id}. Close it before creating another session.",
            status_code=303,
        )

'''
        router = router.replace(marker2, active_guard + "    " + marker2, 1)

write(class_setup_path, router)

# 3) Patch academic_lifecycle_router weekly schedule update
life_path = BACKEND / "app/routers/academic_lifecycle_router.py"
life = read(life_path)

if "validate_weekly_schedule_rule" not in life:
    life = "from app.services.academic_rules import validate_weekly_schedule_rule\n" + life

if "exclude_schedule_id=schedule_id" not in life:
    marker = '''    if not schedule:
        return redirect_class_setup("Schedule not found")
'''
    validation = '''
    ok, message, normalized_start, normalized_end = validate_weekly_schedule_rule(
        db=db,
        class_group_id=class_group_id,
        course_id=course_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        exclude_schedule_id=schedule_id,
    )

    if not ok:
        return redirect_class_setup(message)

    start_time = normalized_start
    end_time = normalized_end

'''
    if marker in life:
        life = life.replace(marker, marker + validation, 1)
    else:
        print("WARNING: Could not insert schedule update validation in academic_lifecycle_router.py")

write(life_path, life)

# 4) Patch session_router to prevent two active sessions for same class group
session_router_path = BACKEND / "app/routers/session_router.py"
session_router = read(session_router_path)

if "class_has_active_session" not in session_router:
    session_router = "from app.services.academic_rules import class_has_active_session\n" + session_router

if "already has an active session" not in session_router:
    marker = "session = ClassSession("
    if marker in session_router:
        guard = '''
    active_session = class_has_active_session(db, class_group_id)
    if active_session:
        return RedirectResponse(
            url=f"/dashboard/sessions?message=This class already has an active session #{active_session.id}. Close it before starting another.",
            status_code=303,
        )

'''
        session_router = session_router.replace(marker, guard + "    " + marker, 1)
    else:
        print("WARNING: Could not find ClassSession creation marker in session_router.py")

write(session_router_path, session_router)

print("")
print("DONE: Academic schedule/session conflict rules applied.")
