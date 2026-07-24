from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class EventSpool:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.path = state_dir / "pending_events.json"

    @staticmethod
    def semantic_key(
        payload: dict[str, Any],
    ) -> str:
        session_id = payload.get("session_id")
        stu_id = payload.get("stu_id")
        face_status = payload.get("face_status")
        attendance_requested = payload.get(
            "attendance_requested",
            True,
        )

        if (
            face_status == "recognized"
            and stu_id
            and attendance_requested
        ):
            return (
                f"attendance:{session_id}:{stu_id}"
            )

        behavior_types = sorted(
            str(item.get("event_type"))
            for item in payload.get(
                "behavior_events",
                [],
            )
            if isinstance(item, dict)
            and item.get("event_type")
        )

        if behavior_types:
            return (
                f"behavior:{session_id}:{stu_id}:"
                + ",".join(behavior_types)
            )

        if face_status == "unknown":
            return (
                f"unknown:{session_id}:"
                f"{payload.get('device_id')}"
            )

        return str(payload.get("event_id"))

    def _ensure_dir(self) -> None:
        self.state_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        try:
            data = json.loads(
                self.path.read_text(
                    encoding="utf-8",
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return []

        if not isinstance(data, list):
            return []

        return [
            item
            for item in data
            if isinstance(item, dict)
        ]

    def save(
        self,
        events: list[dict[str, Any]],
    ) -> None:
        self._ensure_dir()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                events,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def enqueue(
        self,
        payload: dict[str, Any],
    ) -> bool:
        events = self.load()
        key = self.semantic_key(payload)

        if any(
            self.semantic_key(item) == key
            for item in events
        ):
            return False

        events.append(payload)
        self.save(events)
        return True
