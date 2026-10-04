import os

from app.core.auth import IS_CLOUD_DEMO


# "edge": cameras and AI run on the classroom Edge Agent; the server only shows
#         the metadata it receives. Used on Render, which has no webcam.
# "server_camera": legacy local/LAN mode where this server opens the webcam.
EDGE_MODE = "edge"
SERVER_CAMERA_MODE = "server_camera"

MONITORING_MODE = os.getenv(
    "SMART_CLASSROOM_MONITORING_MODE",
    EDGE_MODE if IS_CLOUD_DEMO else SERVER_CAMERA_MODE,
).strip().lower()

if MONITORING_MODE not in {EDGE_MODE, SERVER_CAMERA_MODE}:
    raise RuntimeError(
        "SMART_CLASSROOM_MONITORING_MODE must be 'edge' or 'server_camera'."
    )


def is_edge_monitoring() -> bool:
    return MONITORING_MODE == EDGE_MODE
