from pathlib import Path

BACKEND = Path(__file__).resolve().parent
PROJECT = BACKEND.parent

def write_backend(relative_path: str, content: str):
    path = BACKEND / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Written: {path}")

def read_backend(relative_path: str):
    path = BACKEND / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""

def save_backend(relative_path: str, content: str):
    path = BACKEND / relative_path
    path.write_text(content, encoding="utf-8")
    print(f"Updated: {path}")

def write_project(relative_path: str, content: str):
    path = PROJECT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Written: {path}")

def read_project(relative_path: str):
    path = PROJECT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""

def save_project(relative_path: str, content: str):
    path = PROJECT / relative_path
    path.write_text(content, encoding="utf-8")
    print(f"Updated: {path}")

write_backend("app/routers/admin_router.py", r"""
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
""")

write_backend("app/templates/admin/storage.html", r"""
{% extends "base.html" %}

{% block title %}Admin Storage{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <p class="eyebrow">Phase 12 Storage Management</p>
        <h1>Admin Storage Management</h1>
        <p>Manage classroom monitoring recordings, storage usage, broken files, and legacy video formats.</p>
    </div>
    <a class="btn btn-secondary" href="/dashboard/privacy">Privacy Policy</a>
</div>

<div class="product-note">
    <strong>Product Goal:</strong>
    A real product must allow admins to manage camera recordings, clean broken files, and protect privacy-sensitive data.
</div>

{% if message %}
<div class="success-note">
    ✅ {{ message }}
</div>
{% endif %}

<div class="health-grid">
    <div class="health-card health-ok">
        <h3>Total Recordings</h3>
        <strong>{{ summary.total_recordings }}</strong>
        <p>All recording records in the system.</p>
    </div>

    <div class="health-card health-ok">
        <h3>Total Storage</h3>
        <strong>{{ summary.total_size }}</strong>
        <p>Used by saved recordings.</p>
    </div>

    <div class="health-card health-ok">
        <h3>Playable WebM</h3>
        <strong>{{ summary.playable_count }}</strong>
        <p>Videos ready to watch inside system.</p>
    </div>

    <div class="health-card {% if summary.broken_count > 0 or summary.stuck_count > 0 %}health-error{% else %}health-ok{% endif %}">
        <h3>Needs Attention</h3>
        <strong>{{ summary.broken_count + summary.stuck_count }}</strong>
        <p>{{ summary.broken_count }} broken, {{ summary.stuck_count }} stuck.</p>
    </div>
</div>

<div class="card">
    <div class="section-title-row">
        <h2>Admin Maintenance Actions</h2>
    </div>

    <div class="admin-action-row">
        <form method="post" action="/dashboard/admin/recordings/fix-stuck">
            <button class="btn btn-warning" type="submit">Fix Stuck Recordings</button>
        </form>

        <form method="post" action="/dashboard/admin/recordings/clean-broken" onsubmit="return confirm('Clean broken or too-small recordings?')">
            <button class="btn btn-danger" type="submit">Clean Broken Recordings</button>
        </form>

        <form method="post" action="/dashboard/admin/recordings/delete-legacy-mp4" onsubmit="return confirm('Delete all legacy MP4 recordings? Make sure converted WebM copies already exist.')">
            <button class="btn btn-danger" type="submit">Delete Legacy MP4</button>
        </form>

        <a class="btn btn-secondary" href="/api/admin/storage" target="_blank">Open Storage API</a>
    </div>

    <p class="muted">Storage path: <code>{{ summary.storage_path }}</code></p>
</div>

<div class="card">
    <h2>Recording Records</h2>

    <div class="table-responsive">
        <table class="data-table">
            <thead>
                <tr>
                    <th>File</th>
                    <th>Session</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Stopped</th>
                    <th>Duration</th>
                    <th>Size</th>
                    <th>Type</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for item in recordings %}
                <tr>
                    <td>{{ item.filename }}</td>
                    <td>{{ item.session_id or "-" }}</td>
                    <td><span class="camera-status-pill">{{ item.status }}</span></td>
                    <td>{{ format_kh_datetime(item.started_at) }}</td>
                    <td>{{ format_kh_datetime(item.stopped_at) }}</td>
                    <td>{{ "%.1f"|format(item.duration_seconds) if item.duration_seconds is not none else "-" }}s</td>
                    <td>
                        {% if item.is_playable %}
                        <span class="file-size-good">{{ item.size }}</span>
                        {% elif item.is_legacy %}
                        <span class="file-size-warning">{{ item.size }}</span>
                        {% elif item.is_broken %}
                        <span class="file-size-bad">{{ item.size }}</span>
                        {% else %}
                        <span class="camera-status-pill">{{ item.size }}</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if item.is_playable %}
                        <span class="file-size-good">Playable WebM</span>
                        {% elif item.is_legacy %}
                        <span class="file-size-warning">Legacy MP4</span>
                        {% elif item.is_broken %}
                        <span class="file-size-bad">Broken / Missing</span>
                        {% else %}
                        <span class="camera-status-pill">Recording</span>
                        {% endif %}
                    </td>
                    <td>
                        <div class="recording-action-links">
                            {% if item.is_playable %}
                            <a class="btn btn-primary btn-sm" href="/dashboard/camera-monitoring/recordings/{{ item.id }}">Watch</a>
                            <a class="btn btn-secondary btn-sm" href="/dashboard/camera-monitoring/recordings/{{ item.id }}/download">Download</a>
                            {% endif %}

                            {% if item.is_legacy %}
                            <form method="post" action="/dashboard/camera-monitoring/recordings/{{ item.id }}/convert-webm">
                                <button class="btn btn-warning btn-sm" type="submit">Convert</button>
                            </form>
                            <a class="btn btn-secondary btn-sm" href="/dashboard/camera-monitoring/recordings/{{ item.id }}/download">Download</a>
                            {% endif %}

                            <form method="post" action="/dashboard/admin/recordings/{{ item.id }}/delete" onsubmit="return confirm('Delete this recording from system?')">
                                <button class="btn btn-danger btn-sm" type="submit">Delete</button>
                            </form>
                        </div>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="9" class="muted">No recordings yet.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<div class="danger-note">
    <strong>Privacy Warning:</strong>
    Camera recordings may contain faces and classroom behavior. Do not upload recordings publicly unless all participants agreed.
</div>
{% endblock %}
""")

write_backend("app/templates/admin/privacy.html", r"""
{% extends "base.html" %}

{% block title %}Privacy Policy{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <p class="eyebrow">Phase 12 Privacy Management</p>
        <h1>Storage & Privacy Policy</h1>
        <p>Explain how the system handles face data, attendance records, behavior events, and camera recordings.</p>
    </div>
    <a class="btn btn-secondary" href="/dashboard/admin/storage">Admin Storage</a>
</div>

<div class="product-note">
    <strong>Product Principle:</strong>
    Smart classroom monitoring should be useful for teachers, but it must also be careful with privacy and consent.
</div>

<div class="privacy-grid">
    <div class="card">
        <h2>Data Stored by System</h2>
        <ul class="demo-check-list">
            <li>Student identity and QR code information</li>
            <li>Attendance records per class session</li>
            <li>QR and FACE attendance event logs</li>
            <li>AI behavior monitoring events</li>
            <li>IoT sensor readings and automation logs</li>
            <li>Camera recordings saved in local storage</li>
            <li>Face dataset metadata for recognition training</li>
        </ul>
    </div>

    <div class="card">
        <h2>Privacy Rules</h2>
        <ul class="demo-check-list">
            <li>Use volunteer/demo faces only during project demonstration</li>
            <li>Do not publish raw classroom recordings without permission</li>
            <li>Recordings are stored locally and are ignored by Git</li>
            <li>Teachers/admins can delete recordings from the system</li>
            <li>Event logs are for review and accountability</li>
            <li>Future product version should include user roles and login protection</li>
        </ul>
    </div>
</div>

<div class="card">
    <h2>Recording Retention Policy</h2>
    <p>
        For a school product, recordings should not be kept forever. The admin should review and delete old recordings after they are no longer needed.
    </p>

    <div class="admin-action-row">
        <a class="btn btn-primary" href="/dashboard/admin/storage">Manage Recordings</a>
        <a class="btn btn-secondary" href="/dashboard/system-health">System Health</a>
    </div>
</div>

<div class="danger-note">
    <strong>Important:</strong>
    This project is a prototype. For real deployment, the school should define clear consent, access control, retention period, and data protection policy.
</div>
{% endblock %}
""")

# Patch main.py
main_text = read_backend("app/main.py")
if "phase12_admin_router" not in main_text:
    main_text += """

# Phase 12 Storage, Privacy and Admin Management routes
from app.routers.admin_router import router as phase12_admin_router
app.include_router(phase12_admin_router)
"""
    save_backend("app/main.py", main_text)

# Patch sidebar
base_text = read_backend("app/templates/base.html")
if "/dashboard/admin/storage" not in base_text:
    base_text = base_text.replace(
        "</nav>",
        '    <a href="/dashboard/admin/storage">Admin Storage</a>\n    <a href="/dashboard/privacy">Privacy</a>\n</nav>',
        1,
    )
    save_backend("app/templates/base.html", base_text)

# Patch product health route list
product_router = read_backend("app/routers/product_router.py")
if '("Admin Storage", "/dashboard/admin/storage")' not in product_router:
    product_router = product_router.replace(
        '("System Health", "/dashboard/system-health"),',
        '("System Health", "/dashboard/system-health"),\n        ("Admin Storage", "/dashboard/admin/storage"),\n        ("Privacy", "/dashboard/privacy"),',
        1,
    )

if '{"label": "Storage and privacy admin management", "ready": True}' not in product_router:
    product_router = product_router.replace(
        '{"label": "Product settings and health checks", "ready": True},',
        '{"label": "Product settings and health checks", "ready": True},\n        {"label": "Storage and privacy admin management", "ready": True},',
        1,
    )

save_backend("app/routers/product_router.py", product_router)

# CSS
css_text = read_backend("app/static/css/styles.css")
if "Phase 12 Storage Privacy Admin" not in css_text:
    css_text += r"""

/* Phase 12 Storage Privacy Admin */
.admin-action-row {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    align-items: center;
    margin: 1rem 0;
}

.danger-note {
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #7f1d1d;
    border-radius: 1rem;
    padding: 1rem 1.25rem;
    margin: 1rem 0;
}

.privacy-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
}

@media (max-width: 900px) {
    .privacy-grid {
        grid-template-columns: 1fr;
    }
}
"""
    save_backend("app/static/css/styles.css", css_text)

# Docs
write_project("docs/storage_privacy_admin.md", r"""
# Phase 12 Storage, Privacy and Admin Management

## Goal

Make camera recording management more product-ready.

## Added Pages

```text
/dashboard/admin/storage
/dashboard/privacy
/api/admin/storage
```

## Admin Storage Features

- View total recordings
- View total storage usage
- Identify playable WebM videos
- Identify legacy MP4 videos
- Identify broken or missing recordings
- Fix stuck recordings
- Clean broken recordings
- Delete individual recordings
- Delete legacy MP4 recordings after WebM conversion

## Privacy Policy Features

The system explains:

- What data is stored
- Why camera recordings are sensitive
- Why consent is important
- Why recordings should be deleted after use
- Why event logs support accountability

## Product Note

For real deployment, the next important upgrade is authentication, role-based access, and permission control.
""")

# README update
readme_text = read_project("README.md")
if "Phase 12 Storage, Privacy and Admin Management" not in readme_text:
    readme_text += r"""

## Phase 12 Storage, Privacy and Admin Management

Product pages:

```text
http://127.0.0.1:8000/dashboard/admin/storage
http://127.0.0.1:8000/dashboard/privacy
http://127.0.0.1:8000/api/admin/storage
```

This phase adds admin recording management, cleanup tools, storage summary, and privacy policy pages.
"""
    save_project("README.md", readme_text)

print("")
print("DONE: Phase 12 Storage, Privacy & Admin Management applied.")
