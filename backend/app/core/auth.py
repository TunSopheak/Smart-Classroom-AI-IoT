import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi import Request


SESSION_COOKIE_NAME = "smart_classroom_session"
SESSION_MAX_AGE_SECONDS = 8 * 60 * 60

AUTH_SECRET_KEY = os.getenv(
    "SMART_CLASSROOM_AUTH_SECRET",
    "smart-classroom-demo-secret-change-in-production",
)
DEVICE_API_KEY = os.getenv("SMART_CLASSROOM_DEVICE_API_KEY", "")


DEMO_USERS = {
    "admin": {
        "username": "admin",
        "password": "admin123",
        "role": "admin",
        "display_name": "System Admin",
    },
    "teacher": {
        "username": "teacher",
        "password": "teacher123",
        "role": "teacher",
        "display_name": "Demo Teacher",
    },
    "viewer": {
        "username": "viewer",
        "password": "viewer123",
        "role": "viewer",
        "display_name": "Demo Viewer",
    },
}


PUBLIC_PREFIXES = (
    "/login",
    "/logout",
    "/static",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/api/auth",
)


PROTECTED_PREFIXES = (
    "/dashboard",
    "/api/attendance",
    "/api/sessions",
    "/api/students",
    "/api/teachers",
    "/api/classrooms",
    "/api/subjects",
    "/api/iot",
    "/api/ai-monitoring",
    "/api/face",
    "/api/admin",
    "/api/system-health",
    "/api/camera-monitoring",
    "/api/reports",
    "/api/face-recognition-live",
)


ADMIN_ONLY_PREFIXES = (
    "/dashboard/admin",
    "/dashboard/product-settings",
    "/dashboard/system-health",
    "/api/admin",
    "/api/system-health",
)


TEACHER_OR_ADMIN_PREFIXES = (
    "/api/attendance",
    "/api/sessions",
    "/api/students",
    "/api/teachers",
    "/api/classrooms",
    "/api/subjects",
    "/api/iot",
    "/api/ai-monitoring",
    "/api/face",
    "/dashboard/product-center",
    "/dashboard/qr-attendance",
    "/dashboard/face-training",
    "/dashboard/face-recognition-live",
    "/dashboard/students",
    "/dashboard/sessions",
    "/dashboard/ai-monitoring",
    "/dashboard/camera-monitoring",
    "/dashboard/iot-monitoring",
    "/dashboard/reports",
    "/api/camera-monitoring",
    "/api/reports",
)


VIEWER_ALLOWED_EXACT_PATHS = (
    "/dashboard",
    "/dashboard/product-center",
)


VIEWER_ALLOWED_PREFIXES = (
    "/dashboard/final-demo",
    "/dashboard/privacy",
)


ACADEMIC_PREFIXES = (
    "/dashboard/final-demo",
)


DEVICE_API_PREFIXES = (
    "/api/attendance/face-recognize",
    "/api/attendance/scan-qr",
    "/api/iot/sensor-readings",
    "/api/iot/status",
)


def verify_demo_user(username: str, password: str) -> Optional[dict]:
    user = DEMO_USERS.get(username)

    if not user:
        return None

    if user["password"] != password:
        return None

    return {
        "username": user["username"],
        "role": user["role"],
        "display_name": user["display_name"],
    }


def _sign_payload(encoded_payload: str) -> str:
    return hmac.new(
        AUTH_SECRET_KEY.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_session_cookie(user: dict) -> str:
    payload = {
        "username": user["username"],
        "role": user["role"],
        "display_name": user["display_name"],
        "iat": int(time.time()),
    }

    raw_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(raw_payload).decode("utf-8")
    signature = _sign_payload(encoded_payload)

    return f"{encoded_payload}.{signature}"


def read_session_cookie(cookie_value: str | None) -> Optional[dict]:
    if not cookie_value or "." not in cookie_value:
        return None

    try:
        encoded_payload, signature = cookie_value.rsplit(".", 1)
        expected_signature = _sign_payload(encoded_payload)

        if not hmac.compare_digest(signature, expected_signature):
            return None

        raw_payload = base64.urlsafe_b64decode(encoded_payload.encode("utf-8"))
        payload = json.loads(raw_payload.decode("utf-8"))

        issued_at = int(payload.get("iat", 0))
        if int(time.time()) - issued_at > SESSION_MAX_AGE_SECONDS:
            return None

        username = payload.get("username")
        if username not in DEMO_USERS:
            return None

        return {
            "username": payload.get("username"),
            "role": payload.get("role"),
            "display_name": payload.get("display_name"),
        }

    except Exception:
        return None


def get_current_user_from_request(request: Request) -> Optional[dict]:
    cookie_value = request.cookies.get(SESSION_COOKIE_NAME)
    return read_session_cookie(cookie_value)


def get_device_user_from_request(request: Request) -> Optional[dict]:
    if not any(request.url.path.startswith(prefix) for prefix in DEVICE_API_PREFIXES):
        return None

    if not DEVICE_API_KEY:
        return None

    provided_key = request.headers.get("x-smart-classroom-device-key", "")
    if not hmac.compare_digest(provided_key, DEVICE_API_KEY):
        return None

    return {
        "username": "device",
        "role": "teacher",
        "display_name": "Trusted Classroom Device",
    }


def is_public_path(path: str) -> bool:
    return path == "/" or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


def is_protected_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def user_can_access_path(user: dict, path: str) -> bool:
    role = user.get("role")

    if role == "admin":
        return True

    if any(path.startswith(prefix) for prefix in ADMIN_ONLY_PREFIXES):
        return False

    if any(path.startswith(prefix) for prefix in ACADEMIC_PREFIXES):
        return role == "viewer"

    if role == "teacher":
        return True

    if role == "viewer":
        if path in VIEWER_ALLOWED_EXACT_PATHS:
            return True

        return any(path == prefix or path.startswith(prefix + "/") for prefix in VIEWER_ALLOWED_PREFIXES)

    return False
