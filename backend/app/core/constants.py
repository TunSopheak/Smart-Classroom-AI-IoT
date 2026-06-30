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
    LOW_CONFIDENCE = "low_confidence"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ON = "on"
    OFF = "off"
    ERROR = "error"


class AIMonitoringEventType(str, Enum):
    PHONE_USAGE = "phone_usage"
    SLEEPING = "sleeping"
    LEAVING_SEAT = "leaving_seat"
    HAND_RAISING = "hand_raising"
    ATTENTION_LOW = "attention_low"
    LOOKING_AROUND = "looking_around"
    BOOK_USAGE = "book_usage"
    NO_FACE_DETECTED = "no_face_detected"
    UNKNOWN_FACE = "unknown_face"
    MULTIPLE_FACES = "multiple_faces"


class AIMonitoringSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
