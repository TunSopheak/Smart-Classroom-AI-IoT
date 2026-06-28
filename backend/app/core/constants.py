from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"


class AttendanceStatus(str, Enum):
    PRESENT = "P"
    LATE = "L"
    ABSENT = "A"
    PERMISSION = "Pm"


class AttendanceMethod(str, Enum):
    QR = "QR"
    FACE = "FACE"
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"


class AttendanceEventResult(str, Enum):
    SUCCESS = "success"
    DUPLICATE = "duplicate"
    UNKNOWN = "unknown"
    INVALID = "invalid"
    AFTER_CLOSE = "after_close"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
