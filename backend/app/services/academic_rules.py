
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
