from datetime import datetime
from pathlib import Path

from app.database.database import SessionLocal
from app.models.camera_recording import CameraRecording

BACKEND_ROOT = Path(__file__).resolve().parent
RECORDINGS_DIR = BACKEND_ROOT / "app" / "static" / "recordings"

db = SessionLocal()

items = (
    db.query(CameraRecording)
    .filter(CameraRecording.status == "recording")
    .order_by(CameraRecording.started_at.desc())
    .all()
)

fixed = 0

for item in items:
    file_path = RECORDINGS_DIR / item.filename

    if file_path.exists() and file_path.stat().st_size > 100000:
        item.status = "saved"
        item.stopped_at = datetime.utcnow()

        if item.started_at:
            item.duration_seconds = (item.stopped_at - item.started_at).total_seconds()

        fixed += 1
        print(f"Fixed: {item.filename} | {file_path.stat().st_size} bytes")
    else:
        print(f"Skipped: {item.filename}")

db.commit()
db.close()

print(f"DONE. Fixed stuck recordings: {fixed}")
