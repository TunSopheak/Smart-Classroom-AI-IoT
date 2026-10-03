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

write_file("app/core/timezone.py", r"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


CAMBODIA_TZ = ZoneInfo("Asia/Phnom_Penh")


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
""")

# Patch camera router to pass formatting helpers
router_path = "app/routers/camera_monitoring_router.py"
router_text = read_file(router_path)

if "from app.core.timezone import format_cambodia_datetime, format_cambodia_time" not in router_text:
    router_text = router_text.replace(
        "from app.database.database import get_db",
        "from app.core.timezone import format_cambodia_datetime, format_cambodia_time\nfrom app.database.database import get_db",
        1,
    )

if '"format_kh_datetime": format_cambodia_datetime' not in router_text:
    router_text = router_text.replace(
        '''"behavior_types": BEHAVIOR_TYPES,
        },''',
        '''"behavior_types": BEHAVIOR_TYPES,
            "format_kh_datetime": format_cambodia_datetime,
            "format_kh_time": format_cambodia_time,
        },''',
        1,
    )

if '"format_kh_datetime": format_cambodia_datetime' not in router_text.split('templates.TemplateResponse(')[-1]:
    router_text = router_text.replace(
        '''"recording": recording,
        },''',
        '''"recording": recording,
            "format_kh_datetime": format_cambodia_datetime,
            "format_kh_time": format_cambodia_time,
        },''',
        1,
    )

save_file(router_path, router_text)

# Patch camera monitoring index template
index_path = "app/templates/camera_monitoring/index.html"
index_text = read_file(index_path)

index_text = index_text.replace(
    '{{ event.created_at.strftime("%H:%M:%S") if event.created_at else "-" }}',
    '{{ format_kh_time(event.created_at) }}',
)

index_text = index_text.replace(
    '{{ item.started_at.strftime("%Y-%m-%d %H:%M:%S") if item.started_at else "-" }}',
    '{{ format_kh_datetime(item.started_at) }}',
)

index_text = index_text.replace(
    '{{ item.stopped_at.strftime("%Y-%m-%d %H:%M:%S") if item.stopped_at else "-" }}',
    '{{ format_kh_datetime(item.stopped_at) }}',
)

if "Asia/Phnom_Penh" not in index_text:
    index_text = index_text.replace(
        '<span class="camera-status-pill">Format: WebM / VP8</span>',
        '<span class="camera-status-pill">Format: WebM / VP8</span>\n            <span class="camera-status-pill">Time: Asia/Phnom_Penh</span>',
        1,
    )

save_file(index_path, index_text)

# Patch playback template
playback_path = "app/templates/camera_monitoring/playback.html"
playback_text = read_file(playback_path)

playback_text = playback_text.replace(
    '{{ recording.started_at.strftime("%Y-%m-%d %H:%M:%S") if recording.started_at else "-" }}',
    '{{ format_kh_datetime(recording.started_at) }}',
)

playback_text = playback_text.replace(
    '{{ recording.stopped_at.strftime("%Y-%m-%d %H:%M:%S") if recording.stopped_at else "-" }}',
    '{{ format_kh_datetime(recording.stopped_at) }}',
)

if "Asia/Phnom_Penh" not in playback_text:
    playback_text = playback_text.replace(
        '<strong>Product Feature:</strong>',
        '<strong>Product Feature:</strong> Time is displayed in Asia/Phnom_Penh. ',
        1,
    )

save_file(playback_path, playback_text)

# Docs
write_file("docs/timezone_policy.md", r"""
# Timezone Policy

## Display Timezone

The system displays teacher-facing times using:

```text
Asia/Phnom_Penh
```

## Storage Policy

Database timestamps may be stored as UTC internally.

## Reason

UTC is safer for backend storage, but teachers in Cambodia should see local classroom time on the dashboard.
""")

print("")
print("DONE: Phase 10.2 Cambodia Timezone Display applied.")
