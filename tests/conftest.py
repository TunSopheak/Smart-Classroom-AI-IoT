import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
TEST_DEVICE_KEY = "test-device-key-not-a-real-secret"

# The app reads these at import time, so they must be set before importing it.
# Use a throwaway database and a test-only key so local data is never touched.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="smart_classroom_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TEST_DB_DIR, 'test.db').as_posix()}"
os.environ["SMART_CLASSROOM_DEVICE_API_KEY"] = TEST_DEVICE_KEY
os.environ["APP_ENV"] = "development"
os.environ.pop("RENDER", None)

# Templates and static files are resolved relative to backend/.
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def teacher_client(client):
    client.post("/login", data={"username": "teacher", "password": "teacher123", "next": "/dashboard"})
    yield client
    client.post("/logout")
    client.cookies.clear()


@pytest.fixture
def device_headers():
    return {"x-smart-classroom-device-key": TEST_DEVICE_KEY}


@pytest.fixture
def db(client):
    from app.database.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def active_session(db):
    """Create a fresh active session for the seeded classroom (S001-S005 enrolled).

    Times are naive UTC, matching how the edge API stores captured_at.
    """
    from app.models.class_session import ClassSession
    from app.models.classroom import Classroom
    from app.models.subject import Subject

    db.query(ClassSession).filter(ClassSession.active.is_(True)).update(
        {ClassSession.active: False}
    )

    now = datetime.utcnow().replace(microsecond=0)
    session = ClassSession(
        classroom_id=db.query(Classroom).first().id,
        subject_id=db.query(Subject).first().id,
        title="Edge API test session",
        start_time=now - timedelta(minutes=5),
        late_time=now + timedelta(minutes=10),
        close_time=now + timedelta(hours=1),
        active=True,
        created_by=1,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
