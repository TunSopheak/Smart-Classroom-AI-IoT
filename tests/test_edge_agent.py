import io
from urllib.error import HTTPError, URLError

import pytest

from edge_agent import api_client
from edge_agent.api_client import EdgeAPIClient, EdgeAPIError
from edge_agent.spool import EventSpool


# ------------------------------------------------------------ URL safety


@pytest.mark.parametrize(
    "url",
    [
        "https://smart-classroom.example.com",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
)
def test_allowed_api_urls(url):
    EdgeAPIClient(url, "key")


@pytest.mark.parametrize(
    "url",
    [
        "http://smart-classroom.example.com",
        "http://192.168.1.10:8000",
        "ftp://localhost",
    ],
)
def test_plain_http_to_remote_host_is_permanently_rejected(url):
    with pytest.raises(EdgeAPIError) as error:
        EdgeAPIClient(url, "key")
    assert error.value.retryable is False


# --------------------------------------------------------- retry classification


def _raise_http(code):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, code, "error", {}, io.BytesIO(b'{"detail":"x"}'))

    return fake_urlopen


@pytest.mark.parametrize(
    "code,retryable",
    [
        (400, False),
        (401, False),
        (422, False),
        (408, True),
        (429, True),
        (500, True),
        (503, True),
    ],
)
def test_http_errors_retry_only_when_transient(monkeypatch, code, retryable):
    monkeypatch.setattr(api_client, "urlopen", _raise_http(code))
    client = EdgeAPIClient("https://edge.example.com", "key")

    with pytest.raises(EdgeAPIError) as error:
        client.heartbeat({})
    assert error.value.retryable is retryable


def test_connection_failure_is_retryable(monkeypatch):
    def fake_urlopen(request, timeout):
        raise URLError("offline")

    monkeypatch.setattr(api_client, "urlopen", fake_urlopen)
    client = EdgeAPIClient("https://edge.example.com", "key")

    with pytest.raises(EdgeAPIError) as error:
        client.context()
    assert error.value.retryable is True


def test_device_key_is_sent_as_header(monkeypatch):
    seen = {}

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        seen.update({key.lower(): value for key, value in request.header_items()})
        return FakeResponse(b"{}")

    monkeypatch.setattr(api_client, "urlopen", fake_urlopen)
    EdgeAPIClient("https://edge.example.com", "secret-key").heartbeat({})

    assert seen["x-smart-classroom-device-key"] == "secret-key"


# ------------------------------------------------------------- spool dedupe


def _attendance(event_id, stu_id="S001"):
    return {
        "event_id": event_id,
        "device_id": "edge-01",
        "session_id": 7,
        "face_status": "recognized",
        "stu_id": stu_id,
        "attendance_requested": True,
    }


def test_spool_dedupes_same_student_attendance(tmp_path):
    spool = EventSpool(tmp_path)

    assert spool.enqueue(_attendance("a")) is True
    assert spool.enqueue(_attendance("b")) is False
    assert spool.enqueue(_attendance("c", stu_id="S002")) is True
    assert [item["event_id"] for item in spool.load()] == ["a", "c"]


def test_spool_dedupes_behavior_and_unknown_events(tmp_path):
    spool = EventSpool(tmp_path)
    phone = {
        "event_id": "p1",
        "session_id": 7,
        "stu_id": "S001",
        "face_status": "recognized",
        "attendance_requested": False,
        "behavior_events": [{"event_type": "phone_usage"}],
    }
    unknown = {"event_id": "u1", "session_id": 7, "device_id": "edge-01", "face_status": "unknown"}

    assert spool.enqueue(phone) is True
    assert spool.enqueue({**phone, "event_id": "p2"}) is False
    assert spool.enqueue(unknown) is True
    assert spool.enqueue({**unknown, "event_id": "u2"}) is False
    # Behavior-only and attendance events for the same student are separate.
    assert spool.enqueue(_attendance("a")) is True


def test_spool_survives_corrupt_file(tmp_path):
    spool = EventSpool(tmp_path)
    spool.path.write_text("not json", encoding="utf-8")

    assert spool.load() == []
    assert spool.enqueue(_attendance("a")) is True
