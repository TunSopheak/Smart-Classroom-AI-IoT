from datetime import datetime, timedelta, timezone


# Cambodia timezone is UTC+7.
# Fixed offset is used so the app works on Windows without tzdata.
CAMBODIA_TZ = timezone(timedelta(hours=7), name="Asia/Phnom_Penh")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_cambodia_time(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    # Existing database timestamps are stored as naive UTC.
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
