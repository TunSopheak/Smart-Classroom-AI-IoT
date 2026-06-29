from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.timezone import format_cambodia_datetime
from app.database.database import get_db
from app.models.camera_recording import CameraRecording

router = APIRouter(tags=["Admin Management"])
templates = Jinja2Templates(directory="app/templates")

BACKEND_ROOT = Path(__file__).resolve().parents[2]
RECORDINGS_DIR = BACKEND_ROOT / "app" / "static" / "recordings"


def human_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{round(size_bytes / (1024 * 1024), 2)} MB"
    if size_bytes >= 1024:
        return f"{round(size_bytes / 1024, 2)} KB"
    return f"{size_bytes} bytes"


def get_recording_path(recording: CameraRecording) -> Path:
    return RECORDINGS_DIR / recording.filename


def build_recording_item(recording: CameraRecording) -> dict:
    file_path = get_recording_path(recording)
    exists = file_path.exists()
    size_bytes = file_path.stat().st_size if exists else 0

    filename_lower = recording.filename.lower()
    is_webm = filename_lower.endswith(".webm")
    is_mp4 = filename_lower.endswith(".mp4")
    is_playable = exists and size_bytes > 100000 and is_webm
    is_legacy = exists and size_bytes > 100000 and is_mp4
    is_broken = (not exists) or (exists and size_bytes <= 100000)

    return {
        "id": recording.id,
        "session_id": recording.session_id,
        "filename": recording.filename,
        "status": recording.status,
        "file_path": recording.file_path,
        "started_at": recording.started_at,
        "stopped_at": recording.stopped_at,
        "duration_seconds": recording.duration_seconds,
        "exists": exists,
        "size_bytes": size_bytes,
        "size": human_size(size_bytes),
        "is_webm": is_webm,
        "is_mp4": is_mp4,
        "is_playable": is_playable,
        "is_legacy": is_legacy,
        "is_broken": is_broken,
    }


def build_storage_summary(db: Session) -> dict:
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    recordings = (
        db.query(CameraRecording)
        .order_by(CameraRecording.started_at.desc())
        .all()
    )

    items = [build_recording_item(recording) for recording in recordings]

    total_size = sum(item["size_bytes"] for item in items)
    playable_count = sum(1 for item in items if item["is_playable"])
    legacy_count = sum(1 for item in items if item["is_legacy"])
    broken_count = sum(1 for item in items if item["is_broken"])
    stuck_count = sum(1 for item in items if item["status"] == "recording" and item["size_bytes"] > 100000)

    return {
        "recordings": items,
        "total_recordings": len(items),
        "total_size_bytes": total_size,
        "total_size": human_size(total_size),
        "playable_count": playable_count,
        "legacy_count": legacy_count,
        "broken_count": broken_count,
        "stuck_count": stuck_count,
        "storage_path": str(RECORDINGS_DIR),
    }


@router.get("/dashboard/admin/storage")
def admin_storage_page(request: Request, db: Session = Depends(get_db)):
    summary = build_storage_summary(db)

    return templates.TemplateResponse(
        request,
        "admin/storage.html",
        {
            "request": request,
            "summary": summary,
            "recordings": summary["recordings"],
            "format_kh_datetime": format_cambodia_datetime,
            "message": request.query_params.get("message"),
        },
    )


@router.post("/dashboard/admin/recordings/fix-stuck")
def admin_fix_stuck_recordings(db: Session = Depends(get_db)):
    recordings = (
        db.query(CameraRecording)
        .filter(CameraRecording.status == "recording")
        .order_by(CameraRecording.started_at.desc())
        .all()
    )

    fixed = 0

    for recording in recordings:
        file_path = get_recording_path(recording)

        if file_path.exists() and file_path.stat().st_size > 100000:
            recording.status = "saved"
            recording.stopped_at = datetime.utcnow()

            if recording.started_at:
                recording.duration_seconds = (recording.stopped_at - recording.started_at).total_seconds()

            fixed += 1

    db.commit()

    return RedirectResponse(
        url=f"/dashboard/admin/storage?message=Fixed {fixed} stuck recording(s).",
        status_code=303,
    )


@router.post("/dashboard/admin/recordings/clean-broken")
def admin_clean_broken_recordings(db: Session = Depends(get_db)):
    recordings = db.query(CameraRecording).order_by(CameraRecording.started_at.desc()).all()

    deleted = 0

    for recording in recordings:
        if recording.status == "recording":
            continue

        file_path = get_recording_path(recording)
        missing = not file_path.exists()
        too_small = file_path.exists() and file_path.stat().st_size <= 100000

        if missing or too_small:
            if file_path.exists():
                file_path.unlink()

            db.delete(recording)
            deleted += 1

    db.commit()

    return RedirectResponse(
        url=f"/dashboard/admin/storage?message=Cleaned {deleted} broken recording(s).",
        status_code=303,
    )


@router.post("/dashboard/admin/recordings/delete-legacy-mp4")
def admin_delete_legacy_mp4_recordings(db: Session = Depends(get_db)):
    recordings = db.query(CameraRecording).order_by(CameraRecording.started_at.desc()).all()

    deleted = 0

    for recording in recordings:
        if not recording.filename.lower().endswith(".mp4"):
            continue

        file_path = get_recording_path(recording)

        if file_path.exists():
            file_path.unlink()

        db.delete(recording)
        deleted += 1

    db.commit()

    return RedirectResponse(
        url=f"/dashboard/admin/storage?message=Deleted {deleted} legacy MP4 recording(s).",
        status_code=303,
    )


@router.post("/dashboard/admin/recordings/{recording_id}/delete")
def admin_delete_recording(recording_id: int, db: Session = Depends(get_db)):
    recording = db.query(CameraRecording).filter(CameraRecording.id == recording_id).first()

    if not recording:
        return RedirectResponse(
            url="/dashboard/admin/storage?message=Recording not found.",
            status_code=303,
        )

    filename = recording.filename
    file_path = get_recording_path(recording)

    if file_path.exists():
        file_path.unlink()

    db.delete(recording)
    db.commit()

    return RedirectResponse(
        url=f"/dashboard/admin/storage?message=Deleted {filename}.",
        status_code=303,
    )


@router.get("/dashboard/privacy")
def privacy_page(request: Request):
    return templates.TemplateResponse(
        request,
        "admin/privacy.html",
        {
            "request": request,
        },
    )


@router.get("/api/admin/storage")
def api_admin_storage(db: Session = Depends(get_db)):
    return build_storage_summary(db)
