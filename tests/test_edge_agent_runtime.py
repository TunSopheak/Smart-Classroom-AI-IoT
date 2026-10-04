import os

import numpy as np
import pytest

from edge_agent import runtime
from edge_agent.api_client import EdgeAPIError
from edge_agent.config import EdgeAgentConfig, load_edge_env
from edge_agent.runtime import EdgeAgent
from edge_agent.spool import EventSpool


class StopTest(Exception):
    pass


class FakeCapture:
    def __init__(self, frames=200, working=True):
        self.frames = frames
        self.working = working
        self.reads = 0

    def isOpened(self):
        return True

    def read(self):
        self.reads += 1
        if self.reads > self.frames:
            raise StopTest()
        if not self.working:
            return False, None
        return True, np.zeros((10, 10, 3), dtype=np.uint8)

    def release(self):
        pass


class FakeClient:
    def __init__(self, attendance_result="success", heartbeat_error=None, inference_error=None):
        self.attendance_result = attendance_result
        self.heartbeat_error = heartbeat_error
        self.inference_error = inference_error
        self.heartbeats = []
        self.inferences = []

    def heartbeat(self, payload):
        self.heartbeats.append(payload)
        if self.heartbeat_error and len(self.heartbeats) == 1:
            raise self.heartbeat_error
        return {}

    def context(self):
        return {"active_session": {"session_id": 7, "students": [{"stu_id": "S001"}]}}

    def inference_event(self, payload):
        self.inferences.append(payload)
        if self.inference_error:
            raise self.inference_error
        return {"attendance_result": self.attendance_result, "behavior_event_count": 0}


def _config(tmp_path):
    return EdgeAgentConfig(
        api_url="https://edge.example.com",
        device_key="test-key",
        device_id="test-edge",
        camera_index=0,
        show_window=False,
        face_confidence=0.60,
        stable_frames=6,
        unknown_max_confidence=0.45,
        unknown_stable_frames=6,
        object_every_n_frames=5,
        context_refresh_seconds=3600,
        heartbeat_seconds=3600,
        event_cooldown_seconds=30,
        api_timeout_seconds=5,
        state_dir=tmp_path,
    )


def _agent(tmp_path, monkeypatch, client, capture):
    monkeypatch.setattr(runtime.cv2, "VideoCapture", lambda *args: capture)
    monkeypatch.setattr(runtime.cv2, "destroyAllWindows", lambda: None)
    monkeypatch.setattr(runtime.time, "sleep", lambda seconds: None)

    agent = EdgeAgent(_config(tmp_path))
    agent.client = client
    agent.spool = EventSpool(tmp_path)
    agent.load_models = lambda: None
    # S001 is recognized and stable on every frame.
    agent.process_frame = lambda frame, number: (
        [{"stu_id": "S001", "confidence": 0.8, "distance": 20.0, "bbox": (1, 1, 5, 5), "stable_count": 6}],
        [],
    )
    return agent


@pytest.mark.parametrize("result", ["success", "duplicate", "after_close", "invalid", "low_confidence", "unstable_face"])
def test_recognized_student_is_not_resent_every_frame(tmp_path, monkeypatch, result):
    client = FakeClient(attendance_result=result)
    agent = _agent(tmp_path, monkeypatch, client, FakeCapture(frames=200))

    with pytest.raises(StopTest):
        agent.run()

    # Before the fix, after_close/low_confidence/unstable_face sent 200 events.
    assert len(client.inferences) == 1


def test_permanently_rejected_attendance_is_throttled(tmp_path, monkeypatch):
    client = FakeClient(inference_error=EdgeAPIError("HTTP 400", retryable=False))
    agent = _agent(tmp_path, monkeypatch, client, FakeCapture(frames=200))

    with pytest.raises(StopTest):
        agent.run()

    assert len(client.inferences) == 1


def test_cloud_asleep_at_startup_does_not_stop_agent(tmp_path, monkeypatch):
    client = FakeClient(heartbeat_error=EdgeAPIError("timed out", retryable=True))
    capture = FakeCapture(frames=20)
    agent = _agent(tmp_path, monkeypatch, client, capture)

    with pytest.raises(StopTest):
        agent.run()

    # The agent kept reading frames and still reported attendance.
    assert capture.reads > 20
    assert len(client.inferences) == 1


def test_wrong_device_key_at_startup_stops_agent(tmp_path, monkeypatch):
    client = FakeClient(heartbeat_error=EdgeAPIError("HTTP 401", retryable=False))
    capture = FakeCapture(frames=20)
    agent = _agent(tmp_path, monkeypatch, client, capture)

    with pytest.raises(EdgeAPIError):
        agent.run()

    assert capture.reads == 0


def test_dead_camera_stops_agent_and_reports_camera_down(tmp_path, monkeypatch):
    client = FakeClient()
    capture = FakeCapture(frames=10_000, working=False)
    agent = _agent(tmp_path, monkeypatch, client, capture)

    with pytest.raises(RuntimeError, match="Camera stopped"):
        agent.run()

    assert capture.reads == runtime.MAX_CONSECUTIVE_CAMERA_FAILURES
    assert client.heartbeats[-1]["camera_ready"] is False


def test_shell_variable_overriding_env_file_is_reported(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.edge"
    env_file.write_text(
        "EDGE_TEST_KEY_A=file-value\nEDGE_TEST_KEY_B=same\nEDGE_TEST_KEY_C=from-file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EDGE_TEST_KEY_A", "shell-value")
    monkeypatch.setenv("EDGE_TEST_KEY_B", "same")
    monkeypatch.delenv("EDGE_TEST_KEY_C", raising=False)

    try:
        overrides = load_edge_env(env_file)

        assert overrides == ("EDGE_TEST_KEY_A",)
        assert os.environ["EDGE_TEST_KEY_A"] == "shell-value"
        assert os.environ["EDGE_TEST_KEY_C"] == "from-file"
    finally:
        os.environ.pop("EDGE_TEST_KEY_C", None)
