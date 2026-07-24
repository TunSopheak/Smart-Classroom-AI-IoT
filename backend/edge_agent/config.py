from __future__ import annotations

import os
import re
import socket
from dataclasses import dataclass, replace
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = BACKEND_ROOT / ".env.edge"


def load_edge_env(path: Path = DEFAULT_ENV_PATH) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        line = raw_line.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.getenv(name)
    try:
        value = int(raw) if raw is not None else default
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _float_env(
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw = os.getenv(name)
    try:
        value = float(raw) if raw is not None else default
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _default_device_id() -> str:
    hostname = socket.gethostname().strip() or "classroom-edge"
    normalized = re.sub(
        r"[^A-Za-z0-9._:-]+",
        "-",
        hostname,
    ).strip("-")
    return normalized[:80] or "classroom-edge"


@dataclass(frozen=True)
class EdgeAgentConfig:
    api_url: str
    device_key: str
    device_id: str
    camera_index: int
    show_window: bool
    face_confidence: float
    stable_frames: int
    unknown_max_confidence: float
    unknown_stable_frames: int
    object_every_n_frames: int
    context_refresh_seconds: int
    heartbeat_seconds: int
    event_cooldown_seconds: int
    api_timeout_seconds: int
    state_dir: Path

    @classmethod
    def load(cls) -> "EdgeAgentConfig":
        load_edge_env()
        return cls(
            api_url=os.getenv(
                "SMART_CLASSROOM_EDGE_API_URL",
                "http://127.0.0.1:8000",
            ).strip().rstrip("/"),
            device_key=os.getenv(
                "SMART_CLASSROOM_DEVICE_API_KEY",
                "",
            ),
            device_id=os.getenv(
                "SMART_CLASSROOM_EDGE_DEVICE_ID",
                _default_device_id(),
            ).strip()[:80],
            camera_index=_int_env(
                "SMART_CLASSROOM_EDGE_CAMERA_INDEX",
                0,
                0,
                20,
            ),
            show_window=_bool_env(
                "SMART_CLASSROOM_EDGE_SHOW_WINDOW",
                True,
            ),
            face_confidence=_float_env(
                "SMART_CLASSROOM_EDGE_FACE_CONFIDENCE",
                0.60,
                0.0,
                1.0,
            ),
            stable_frames=_int_env(
                "SMART_CLASSROOM_EDGE_STABLE_FRAMES",
                6,
                1,
                120,
            ),
            unknown_max_confidence=_float_env(
                "SMART_CLASSROOM_EDGE_UNKNOWN_MAX_CONFIDENCE",
                0.45,
                0.0,
                1.0,
            ),
            unknown_stable_frames=_int_env(
                "SMART_CLASSROOM_EDGE_UNKNOWN_STABLE_FRAMES",
                6,
                1,
                120,
            ),
            object_every_n_frames=_int_env(
                "SMART_CLASSROOM_EDGE_OBJECT_EVERY_N_FRAMES",
                5,
                1,
                120,
            ),
            context_refresh_seconds=_int_env(
                "SMART_CLASSROOM_EDGE_CONTEXT_REFRESH_SECONDS",
                15,
                5,
                3600,
            ),
            heartbeat_seconds=_int_env(
                "SMART_CLASSROOM_EDGE_HEARTBEAT_SECONDS",
                30,
                10,
                3600,
            ),
            event_cooldown_seconds=_int_env(
                "SMART_CLASSROOM_EDGE_EVENT_COOLDOWN_SECONDS",
                30,
                5,
                3600,
            ),
            api_timeout_seconds=_int_env(
                "SMART_CLASSROOM_EDGE_API_TIMEOUT_SECONDS",
                15,
                2,
                120,
            ),
            state_dir=BACKEND_ROOT / "edge_agent_state",
        )

    def with_show_window(
        self,
        show_window: bool,
    ) -> "EdgeAgentConfig":
        return replace(
            self,
            show_window=show_window,
        )

    def validate_live(self) -> None:
        if not self.device_key:
            raise ValueError(
                "SMART_CLASSROOM_DEVICE_API_KEY is missing. "
                "Store it only in backend/.env.edge."
            )
        if not self.device_id:
            raise ValueError(
                "SMART_CLASSROOM_EDGE_DEVICE_ID is missing."
            )

        if self.unknown_max_confidence >= self.face_confidence:
            raise ValueError(
                "SMART_CLASSROOM_EDGE_UNKNOWN_MAX_CONFIDENCE "
                "must be lower than FACE_CONFIDENCE."
            )
