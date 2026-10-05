import pytest


@pytest.fixture
def s004_with_stored_code(db):
    """Temporarily store a custom QR value on S004, then restore its signed code."""
    from app.models.student import Student
    from app.services.qr_service import build_student_qr_code

    student = db.query(Student).filter(Student.stu_id == "S004").one()

    def store(value):
        student.qr_code = value
        db.commit()

    yield store
    store(build_student_qr_code("S004"))


def _scan(client, headers, qr_code, session_id):
    return client.post(
        "/api/attendance/scan-qr",
        json={"qr_code": qr_code, "session_id": session_id},
        headers=headers,
    ).json()


@pytest.mark.parametrize(
    "qr_code",
    [
        "SC-STUDENT-S004",  # legacy unsigned, guessable
        "S004",
        "SCQR:v1:S004:0000000000000000",  # forged signature
    ],
)
def test_unsigned_or_forged_qr_is_rejected(client, device_headers, db, active_session, s004_with_stored_code, qr_code):
    from app.models.attendance_record import AttendanceRecord
    from app.models.student import Student

    # Simulate a database that still stores the old guessable value.
    s004_with_stored_code(qr_code)
    student = db.query(Student).filter(Student.stu_id == "S004").one()

    body = _scan(client, device_headers, qr_code, active_session.id)

    assert body["result"] == "unknown"
    record = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == active_session.id, AttendanceRecord.student_id == student.id)
        .first()
    )
    assert record is None or record.status == "A"


def test_signed_qr_marks_attendance(client, device_headers, active_session):
    from app.services.qr_service import build_student_qr_code

    body = _scan(client, device_headers, build_student_qr_code("S005"), active_session.id)
    assert body["result"] == "success"


def test_seeded_students_have_signed_qr(db):
    from app.models.student import Student
    from app.services.student_qr_service import has_valid_signed_qr

    for stu_id in ("S001", "S002", "S003", "S004", "S005"):
        assert has_valid_signed_qr(db.query(Student).filter(Student.stu_id == stu_id).one())


def test_startup_upgrade_replaces_legacy_codes(db, monkeypatch):
    from app.models.student import Student
    from app.services import student_qr_service

    monkeypatch.setattr(student_qr_service, "generate_student_qr_image", lambda stu_id, code: f"/static/generated_qr/{stu_id}.png")
    db.add(Student(stu_id="S950", name="Legacy Card", qr_code="SC-STUDENT-S950", active=True))
    db.commit()

    assert student_qr_service.upgrade_unsigned_qr_codes(db) >= 1

    student = db.query(Student).filter(Student.stu_id == "S950").one()
    assert student_qr_service.has_valid_signed_qr(student)
    assert student_qr_service.upgrade_unsigned_qr_codes(db) == 0
