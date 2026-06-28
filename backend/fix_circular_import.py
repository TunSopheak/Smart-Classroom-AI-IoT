from pathlib import Path

print("Fixing SQLAlchemy circular import...")

Path("app/database/base.py").write_text(r'''from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
''', encoding="utf-8")

Path("app/models/__init__.py").write_text(r'''# Import all SQLAlchemy models here so Base.metadata can discover them
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
''', encoding="utf-8")

main_path = Path("app/main.py")
text = main_path.read_text(encoding="utf-8")

if "import app.models  # noqa: F401" not in text:
    text = text.replace(
        "from app.database.seed import seed_demo_data",
        "from app.database.seed import seed_demo_data\nimport app.models  # noqa: F401",
    )

main_path.write_text(text, encoding="utf-8")

print("DONE: circular import fixed.")
print("Updated:")
print("- app/database/base.py")
print("- app/models/__init__.py")
print("- app/main.py")
