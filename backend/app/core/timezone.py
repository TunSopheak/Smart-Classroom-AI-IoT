"""Time policy.

Two kinds of timestamps are stored, both as naive datetimes:

* Classroom time (Asia/Phnom_Penh wall clock): class session start/late/close
  times, attendance check-in times (first_seen_time, attendance event
  timestamps) and weekly schedules. Attendance rules compare these directly,
  so every check-in must be converted to classroom time first. Shown as-is.
* UTC: audit timestamps such as created_at, updated_at, last_seen,
  recording start/stop and Edge captured_at. Shown with the kh_datetime /
  kh_time template filters.

Never use datetime.now() or date.today(): on Render the server clock is UTC.
"""

from datetime import date, datetime, timedelta, timezone


# Cambodia is UTC+7 with no daylight saving time. A fixed offset works on
# Windows without the tzdata package.
CAMBODIA_TZ = timezone(timedelta(hours=7), name="Asia/Phnom_Penh")


def utc_now() -> datetime:
    """Naive UTC now, for audit timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def classroom_now() -> datetime:
    """Naive Cambodia wall-clock now (whole seconds), for attendance times."""
    return datetime.now(CAMBODIA_TZ).replace(tzinfo=None, microsecond=0)


def classroom_today() -> date:
    return classroom_now().date()


def to_classroom_time(value: datetime) -> datetime:
    """Convert a timezone-aware (or naive UTC) datetime to naive classroom time."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(CAMBODIA_TZ).replace(tzinfo=None, microsecond=0)


def to_cambodia_time(value: datetime | None) -> datetime | None:
    """Convert a naive UTC audit timestamp to aware Cambodia time."""
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(CAMBODIA_TZ)


def format_cambodia_datetime(value: datetime | None) -> str:
    kh_time = to_cambodia_time(value)
    if kh_time is None:
        return "-"

    return kh_time.strftime("%Y-%m-%d %H:%M:%S")


def format_cambodia_time(value: datetime | None) -> str:
    kh_time = to_cambodia_time(value)
    if kh_time is None:
        return "-"

    return kh_time.strftime("%H:%M:%S")
