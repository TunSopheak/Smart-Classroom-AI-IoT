from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.timezone import CAMBODIA_TZ, classroom_now, to_classroom_time


def test_to_classroom_time_converts_utc():
    assert to_classroom_time(datetime(2026, 10, 5, 1, 0, tzinfo=timezone.utc)) == datetime(2026, 10, 5, 8, 0)
    # Naive input is treated as UTC.
    assert to_classroom_time(datetime(2026, 10, 5, 23, 30)) == datetime(2026, 10, 6, 6, 30)


def test_classroom_now_is_cambodia_wall_clock():
    expected = datetime.now(CAMBODIA_TZ).replace(tzinfo=None)
    assert abs((classroom_now() - expected).total_seconds()) < 5


def _late_session(db):
    """Active session that started 30 min ago with the late cutoff 10 min ago (classroom time)."""
    from app.models.class_session import ClassSession
    from app.models.classroom import Classroom
    from app.models.subject import Subject

    db.query(ClassSession).filter(ClassSession.active.is_(True)).update({ClassSession.active: False})
    now = classroom_now()
    session = ClassSession(
        classroom_id=db.query(Classroom).first().id,
        subject_id=db.query(Subject).first().id,
        title="Late check-in test",
        start_time=now - timedelta(minutes=30),
        late_time=now - timedelta(minutes=10),
        close_time=now + timedelta(hours=1),
        active=True,
        created_by=1,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def test_edge_check_in_after_late_time_is_late(client, device_headers, db):
    # Regression: captured_at (UTC) was compared with classroom-time session
    # times, so a late Edge check-in was always marked Present.
    from app.models.attendance_record import AttendanceRecord

    session = _late_session(db)
    body = client.post(
        "/api/edge/v1/inference-events",
        json={
            "event_id": str(uuid4()),
            "device_id": "tz-edge",
            "session_id": session.id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "face_status": "recognized",
            "stu_id": "S002",
            "confidence": 0.8,
            "lbph_distance": 20.0,
            "stable_frame_count": 6,
        },
        headers=device_headers,
    ).json()

    record = db.get(AttendanceRecord, body["attendance_record_id"])
    assert body["attendance_result"] == "success"
    assert record.status == "L"
    # Check-in time is stored in classroom time.
    assert abs((record.first_seen_time - classroom_now()).total_seconds()) < 60


def test_qr_check_in_uses_classroom_time(client, device_headers, db):
    from app.models.attendance_record import AttendanceRecord
    from app.models.student import Student
    from app.services.qr_service import build_student_qr_code

    session = _late_session(db)
    response = client.post(
        "/api/attendance/scan-qr",
        json={"qr_code": build_student_qr_code("S003"), "session_id": session.id},
        headers=device_headers,
    )
    assert response.status_code == 200

    student = db.query(Student).filter(Student.stu_id == "S003").one()
    record = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.session_id == session.id, AttendanceRecord.student_id == student.id)
        .one()
    )
    assert record.status == "L"
    assert abs((record.first_seen_time - classroom_now()).total_seconds()) < 60


def test_audit_timestamps_render_in_cambodia_time():
    from app.core.templating import templates

    template = templates.env.from_string("{{ value|kh_datetime }} {{ missing|kh_time }}")
    assert template.render(value=datetime(2026, 10, 5, 1, 0, 0), missing=None) == "2026-10-05 08:00:00 -"
