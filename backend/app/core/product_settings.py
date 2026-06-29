import json
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_DIR = BACKEND_ROOT / "app" / "static" / "data"
SETTINGS_FILE = SETTINGS_DIR / "product_settings.json"


DEFAULT_PRODUCT_SETTINGS = {
    "product_name": "Smart Classroom AI Monitoring",
    "school_name": "RUPP",
    "timezone": "Asia/Phnom_Penh",
    "camera_index": 0,
    "recording_format": "webm_vp8",
    "auto_behavior_default": False,
    "attention_low_seconds": 2.5,
    "leaving_seat_seconds": 5.0,
    "sleeping_seconds": 4.0,
    "behavior_cooldown_seconds": 20.0,
    "recording_storage_note": "Recordings are saved locally inside backend/app/static/recordings.",
    "privacy_note": "Use volunteer/demo faces only during project demonstration.",
}


def ensure_settings_file() -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(
            json.dumps(DEFAULT_PRODUCT_SETTINGS, indent=2),
            encoding="utf-8",
        )


def load_product_settings() -> dict[str, Any]:
    ensure_settings_file()

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    settings = DEFAULT_PRODUCT_SETTINGS.copy()
    settings.update(data)
    return settings


def save_product_settings(settings: dict[str, Any]) -> dict[str, Any]:
    ensure_settings_file()

    cleaned = DEFAULT_PRODUCT_SETTINGS.copy()
    cleaned.update(settings)

    SETTINGS_FILE.write_text(
        json.dumps(cleaned, indent=2),
        encoding="utf-8",
    )

    return cleaned
