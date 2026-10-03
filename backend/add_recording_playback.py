from pathlib import Path

ROOT = Path(__file__).resolve().parent

def write_file(relative_path: str, content: str):
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Written: {path}")

def read_file(relative_path: str):
    path = ROOT / relative_path
    return path.read_text(encoding="utf-8") if path.exists() else ""

def save_file(relative_path: str, content: str):
    path = ROOT / relative_path
    path.write_text(content, encoding="utf-8")
    print(f"Updated: {path}")

# 1) Patch camera router with playback page + download route
router_path = "app/routers/camera_monitoring_router.py"
router_text = read_file(router_path)

if "FileResponse" not in router_text:
    router_text = router_text.replace(
        "from fastapi.responses import RedirectResponse, StreamingResponse",
        "from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse",
    )

if "from pathlib import Path" not in router_text:
    router_text = router_text.replace(
        "from datetime import datetime",
        "from datetime import datetime\nfrom pathlib import Path",
    )

if "RECORDINGS_DIR" not in router_text:
    router_text = router_text.replace(
        'templates = Jinja2Templates(directory="app/templates")',
        'templates = Jinja2Templates(directory="app/templates")\nBACKEND_ROOT = Path(__file__).resolve().parents[2]\nRECORDINGS_DIR = BACKEND_ROOT / "app" / "static" / "recordings"',
    )

if '@router.get("/dashboard/camera-monitoring/recordings/{recording_id}")' not in router_text:
    router_text += r'''


@router.get("/dashboard/camera-monitoring/recordings/{recording_id}")
def dashboard_recording_playback(
    recording_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    recording = (
        db.query(CameraRecording)
        .filter(CameraRecording.id == recording_id)
        .first()
    )

    return templates.TemplateResponse(
        request,
        "camera_monitoring/playback.html",
        {
            "request": request,
            "recording": recording,
        },
    )


@router.get("/dashboard/camera-monitoring/recordings/{recording_id}/download")
def dashboard_recording_download(
    recording_id: int,
    db: Session = Depends(get_db),
):
    recording = (
        db.query(CameraRecording)
        .filter(CameraRecording.id == recording_id)
        .first()
    )

    if not recording:
        return {
            "success": False,
            "message": "Recording not found.",
        }

    file_path = RECORDINGS_DIR / recording.filename

    if not file_path.exists():
        return {
            "success": False,
            "message": "Recording file is missing from storage.",
        }

    return FileResponse(
        path=str(file_path),
        filename=recording.filename,
        media_type="video/mp4",
    )
'''
    save_file(router_path, router_text)

# 2) Add playback template
write_file("app/templates/camera_monitoring/playback.html", r"""
{% extends "base.html" %}

{% block title %}Recording Playback{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <p class="eyebrow">Phase 9.2 Recording Playback</p>
        <h1>Recording Playback</h1>
        <p>Watch the saved classroom monitoring video inside the system.</p>
    </div>
    <a class="btn btn-secondary" href="/dashboard/camera-monitoring">Back Camera Monitoring</a>
</div>

{% if recording %}
<div class="product-note">
    <strong>Product Feature:</strong>
    The teacher can watch the recording inside the system and can also download the video file if needed.
</div>

<div class="card">
    <h2>{{ recording.filename }}</h2>

    <div class="recording-player-wrap">
        <video class="recording-player" controls preload="metadata">
            <source src="{{ recording.file_path }}" type="video/mp4">
            Your browser does not support video playback.
        </video>
    </div>

    <div class="recording-meta-grid">
        <div>
            <span class="muted">Session</span>
            <strong>{{ recording.session_id or "-" }}</strong>
        </div>
        <div>
            <span class="muted">Status</span>
            <strong>{{ recording.status }}</strong>
        </div>
        <div>
            <span class="muted">Started</span>
            <strong>{{ recording.started_at.strftime("%Y-%m-%d %H:%M:%S") if recording.started_at else "-" }}</strong>
        </div>
        <div>
            <span class="muted">Stopped</span>
            <strong>{{ recording.stopped_at.strftime("%Y-%m-%d %H:%M:%S") if recording.stopped_at else "-" }}</strong>
        </div>
        <div>
            <span class="muted">Duration</span>
            <strong>{{ "%.1f"|format(recording.duration_seconds) if recording.duration_seconds is not none else "-" }}s</strong>
        </div>
    </div>

    <div class="quick-ai-grid">
        <a class="btn btn-primary" href="{{ recording.file_path }}" target="_blank">Open Raw Video</a>
        <a class="btn btn-secondary" href="/dashboard/camera-monitoring/recordings/{{ recording.id }}/download">Download Video</a>
    </div>
</div>

<div class="card">
    <h2>What This Video Should Show</h2>
    <ul class="demo-check-list">
        <li>Smart Classroom overlay</li>
        <li>Face frame box</li>
        <li>REC indicator during recording</li>
        <li>Behavior overlay if behavior button was clicked while recording</li>
    </ul>
</div>
{% else %}
<div class="card">
    <h2>Recording not found</h2>
    <p class="muted">The selected recording does not exist.</p>
</div>
{% endif %}
{% endblock %}
""")

# 3) Patch index template links
index_path = "app/templates/camera_monitoring/index.html"
index_text = read_file(index_path)

old = r'''<td>
                        {% if item.status == "saved" %}
                        <a href="{{ item.file_path }}" target="_blank">Open Video</a>
                        {% else %}
                        <span class="muted">Recording...</span>
                        {% endif %}
                    </td>'''

new = r'''<td>
                        {% if item.status == "saved" %}
                        <div class="recording-action-links">
                            <a href="/dashboard/camera-monitoring/recordings/{{ item.id }}">Watch</a>
                            <a href="/dashboard/camera-monitoring/recordings/{{ item.id }}/download">Download</a>
                        </div>
                        {% else %}
                        <span class="muted">Recording...</span>
                        {% endif %}
                    </td>'''

if old in index_text:
    index_text = index_text.replace(old, new)
    save_file(index_path, index_text)
elif "Open Video" in index_text and "recording-action-links" not in index_text:
    index_text = index_text.replace(
        '<a href="{{ item.file_path }}" target="_blank">Open Video</a>',
        '<div class="recording-action-links"><a href="/dashboard/camera-monitoring/recordings/{{ item.id }}">Watch</a><a href="/dashboard/camera-monitoring/recordings/{{ item.id }}/download">Download</a></div>',
    )
    save_file(index_path, index_text)

# 4) CSS
css_path = "app/static/css/styles.css"
css_text = read_file(css_path)

if "Phase 9.2 Recording Playback" not in css_text:
    css_text += r"""

/* Phase 9.2 Recording Playback */
.recording-player-wrap {
    background: #020617;
    border-radius: 1rem;
    overflow: hidden;
    border: 1px solid #1e293b;
    margin: 1rem 0;
}

.recording-player {
    width: 100%;
    max-height: 620px;
    display: block;
    background: #020617;
}

.recording-meta-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 1rem;
    margin: 1rem 0;
}

.recording-meta-grid div {
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    padding: 0.85rem;
    border-radius: 0.85rem;
}

.recording-meta-grid span,
.recording-meta-grid strong {
    display: block;
}

.recording-action-links {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.demo-check-list {
    line-height: 1.8;
}

@media (max-width: 1000px) {
    .recording-meta-grid {
        grid-template-columns: 1fr 1fr;
    }
}

@media (max-width: 700px) {
    .recording-meta-grid {
        grid-template-columns: 1fr;
    }
}
"""
    save_file(css_path, css_text)

# 5) Docs
write_file("docs/recording_playback.md", r"""
# Recording Playback

## Product Requirement

Teachers should be able to:

1. Watch saved classroom monitoring videos inside the system
2. Download the video if needed

## Implementation

Camera Monitoring records videos into:

```text
backend/app/static/recordings/
```

The system provides:

- Recording history table
- Watch page with HTML video player
- Download route

## Why Direct MP4 Link May Download

Some browsers or download managers treat direct `.mp4` links as downloadable files.  
A playback page solves this by embedding the MP4 inside a `<video controls>` element.
""")

print("")
print("DONE: Phase 9.2 Recording Playback page applied.")
