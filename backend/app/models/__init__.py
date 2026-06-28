# Import all SQLAlchemy models here so Base.metadata can discover them
# without causing circular imports inside app.database.base.

from app.models.user import User
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.classroom import Classroom
from app.models.subject import Subject
from app.models.enrollment import Enrollment
from app.models.class_session import ClassSession
from app.models.attendance_record import AttendanceRecord
from app.models.attendance_event import AttendanceEvent
from app.models.face_profile import FaceProfile
from app.models.ai_event import AIEvent
from app.models.device import Device
from app.models.sensor_reading import SensorReading

__all__ = [
    "User",
    "Teacher",
    "Student",
    "Classroom",
    "Subject",
    "Enrollment",
    "ClassSession",
    "AttendanceRecord",
    "AttendanceEvent",
    "FaceProfile",
    "AIEvent",
    "Device",
    "SensorReading",
]

from app.models.ai_monitoring_event import AIMonitoringEvent
