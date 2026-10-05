"""Import every SQLAlchemy model so Base.metadata knows all tables.

Keeping the imports here (instead of in app.database.base) avoids
circular imports.
"""

from app.models.academic import ClassGroup, Course, StudentEnrollment, WeeklySchedule
from app.models.ai_event import AIEvent
from app.models.ai_monitoring_event import AIMonitoringEvent
from app.models.attendance_event import AttendanceEvent
from app.models.attendance_record import AttendanceRecord
from app.models.camera_recording import CameraRecording
from app.models.class_session import ClassSession
from app.models.classroom import Classroom
from app.models.device import Device
from app.models.edge_device import EdgeDevice
from app.models.edge_inference_event import EdgeInferenceEvent
from app.models.enrollment import Enrollment
from app.models.face_profile import FaceProfile
from app.models.iot_automation_event import IoTAutomationEvent
from app.models.sensor_reading import SensorReading
from app.models.student import Student
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.user import User

__all__ = [
    "AIEvent",
    "AIMonitoringEvent",
    "AttendanceEvent",
    "AttendanceRecord",
    "CameraRecording",
    "ClassGroup",
    "ClassSession",
    "Classroom",
    "Course",
    "Device",
    "EdgeDevice",
    "EdgeInferenceEvent",
    "Enrollment",
    "FaceProfile",
    "IoTAutomationEvent",
    "SensorReading",
    "Student",
    "StudentEnrollment",
    "Subject",
    "Teacher",
    "User",
    "WeeklySchedule",
]
