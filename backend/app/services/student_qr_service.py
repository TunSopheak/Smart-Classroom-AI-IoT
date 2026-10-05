from sqlalchemy.orm import Session

from app.models.student import Student
from app.services.qr_service import (
    build_student_qr_code,
    generate_student_qr_image,
    parse_signed_student_qr,
)


def has_valid_signed_qr(student: Student) -> bool:
    return bool(student.qr_code) and parse_signed_student_qr(student.qr_code) == student.stu_id


def ensure_student_qr(db: Session, student: Student) -> Student:
    """Give a student a signed QR value and a fresh QR image."""
    if not has_valid_signed_qr(student):
        student.qr_code = build_student_qr_code(student.stu_id)

    student.qr_image_path = generate_student_qr_image(student.stu_id, student.qr_code)
    db.commit()
    db.refresh(student)
    return student


def upgrade_unsigned_qr_codes(db: Session) -> int:
    """Replace legacy unsigned QR values (for example SC-STUDENT-S001).

    The scanner only accepts signed codes, so printed cards for upgraded
    students must be reprinted. Returns the number of students upgraded.
    """
    upgraded = 0
    for student in db.query(Student).all():
        if has_valid_signed_qr(student):
            continue
        student.qr_code = build_student_qr_code(student.stu_id)
        student.qr_image_path = generate_student_qr_image(student.stu_id, student.qr_code)
        upgraded += 1

    if upgraded:
        db.commit()
    return upgraded
