from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.constants import AttendanceMethod, AttendanceStatus, UserRole
from app.core.security import hash_password
from app.database.database import SessionLocal
from app.models.attendance_record import AttendanceRecord
from app.models.class_session import ClassSession
from app.models.classroom import Classroom
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.user import User
from app.services.academic_service import seed_academic_demo_data


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        if db.query(User).first():
            seed_academic_demo_data(db)
            return

        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role=UserRole.ADMIN.value,
            active=True,
        )
        db.add(admin)
        db.flush()

        teacher = Teacher(
            user_id=admin.id,
            name="Teacher Heng Sovannarith",
            email="teacher@example.com",
            phone="012345678",
            active=True,
        )
        db.add(teacher)
        db.flush()

        classroom = Classroom(
            code="CS-M4-Y3-G27",
            name="Computer Science M4 Year 3 Generation 27",
            section="Group 1",
            shift="Evening",
            room="IoT Lab",
            active=True,
        )
        db.add(classroom)
        db.flush()

        subject = Subject(
            code="IOT301",
            name="IoT Project",
            teacher_id=teacher.id,
            active=True,
        )
        db.add(subject)
        db.flush()

        students = [
            Student(stu_id="S001", name="Tun Sopheak", gender="M", qr_code="SC-STUDENT-S001", face_dataset_path="ai_module/face_recognition/datasets/S001", active=True),
            Student(stu_id="S002", name="Thon Serey Rothana", gender="M", qr_code="SC-STUDENT-S002", face_dataset_path="ai_module/face_recognition/datasets/S002", active=True),
            Student(stu_id="S003", name="Tit Sokhom", gender="M", qr_code="SC-STUDENT-S003", face_dataset_path="ai_module/face_recognition/datasets/S003", active=True),
            Student(stu_id="S004", name="Tep Makhon", gender="M", qr_code="SC-STUDENT-S004", face_dataset_path="ai_module/face_recognition/datasets/S004", active=True),
            Student(stu_id="S005", name="Theam VanTim", gender="M", qr_code="SC-STUDENT-S005", face_dataset_path="ai_module/face_recognition/datasets/S005", active=True),
        ]
        db.add_all(students)
        db.flush()

        for student in students:
            db.add(Enrollment(classroom_id=classroom.id, student_id=student.id, active=True))

        now = datetime.now().replace(second=0, microsecond=0)
        session = ClassSession(
            classroom_id=classroom.id,
            subject_id=subject.id,
            title="Smart Classroom MVP Demo Session",
            start_time=now,
            late_time=now + timedelta(minutes=15),
            close_time=now + timedelta(hours=2),
            active=True,
            created_by=admin.id,
        )
        db.add(session)
        db.flush()

        # Default records start as absent until QR/face/manual updates happen in later phases.
        for student in students:
            db.add(
                AttendanceRecord(
                    session_id=session.id,
                    student_id=student.id,
                    status=AttendanceStatus.ABSENT.value,
                    method=AttendanceMethod.SYSTEM.value,
                )
            )

        db.commit()
        seed_academic_demo_data(db)
    finally:
        db.close()
