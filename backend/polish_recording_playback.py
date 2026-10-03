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

router_path = "app/routers/camera_monitoring_router.py"
router_text = read_file(router_path)

# Add helper functions if missing
if "def enrich_recording_file_info" not in router_text:
    insert_after = 'BEHAVIOR_TYPES = [\n    "phone_usage",\n    "sleeping",\n    "leaving_seat",\n    "attention_low",\n    "hand_raising",\n]\n'
    helper = r'''

def get_recording_file_path(recording: CameraRecording):
    return RECORDINGS_DIR / recording.filename


def enrich_recording_file_info(recording: CameraRecording):
    file_path = get_recording_file_path(recording)

    recording.file_exists = file_path.exists()
    recording.file_size_bytes = file_path.stat().st_size if file_path.exists() else 0
    recording.file_size_mb = round(recording.file_size_bytes / (1024 * 1024), 2)
    recording.is_playable = recording.file_exists and recording.file_size_bytes > 100000

    return recording
'''
    router_text = router_text.replace(insert_after, insert_after + helper)

# Enrich recording list
if "recordings = [enrich_recording_file_info(item) for item in recordings]" not in router_text:
    router_text = router_text.replace(
        '''recordings = (
        db.query(CameraRecording)
        .order_by(CameraRecording.started_at.desc())
        .limit(20)
        .all()
    )''',
        '''recordings = (
        db.query(CameraRecording)
        .order_by(CameraRecording.started_at.desc())
        .limit(20)
        .all()
    )
    recordings = [enrich_recording_file_info(item) for item in recordings]''',
    )

# Enrich playback recording
if "recording = enrich_recording_file_info(recording) if recording else None" not in router_text:
    router_text = router_text.replace(
        '''recording = (
        db.query(CameraRecording)
        .filter(CameraRecording.id == recording_id)
        .first()
    )

    return templates.TemplateResponse(''',
        '''recording = (
        db.query(CameraRecording)
        .filter(CameraRecording.id == recording_id)
        .first()
    )
    recording = enrich_recording_file_info(recording) if recording else None

    return templates.TemplateResponse(''',
    )

# Make download route use helper
router_text = router_text.replace(
    '''file_path = RECORDINGS_DIR / recording.filename''',
    '''file_path = get_recording_file_path(recording)''',
)

save_file(router_path, router_text)

# Update camera monitoring index table
index_path = "app/templates/camera_monitoring/index.html"
index_text = read_file(index_path)

if "<th>Size</th>" not in index_text:
    index_text = index_text.replace(
        "<th>Duration</th>\n                    <th>Open</th>",
        "<th>Duration</th>\n                    <th>Size</th>\n                    <th>Action</th>",
    )

if "{{ item.file_size_mb }}" not in index_text:
    index_text = index_text.replace(
        '''<td>{{ "%.1f"|format(item.duration_seconds) if item.duration_seconds is not none else "-" }}s</td>
                    <td>
                        {% if item.status == "saved" %}
                        <div class="recording-action-links">
                            <a href="/dashboard/camera-monitoring/recordings/{{ item.id }}">Watch</a>
                            <a href="/dashboard/camera-monitoring/recordings/{{ item.id }}/download">Download</a>
                        </div>
                        {% else %}
                        <span class="muted">Recording...</span>
                        {% endif %}
                    </td>''',
        '''<td>{{ "%.1f"|format(item.duration_seconds) if item.duration_seconds is not none else "-" }}s</td>
                    <td>
                        {% if item.file_exists %}
                            {% if item.is_playable %}
                                <span class="file-size-good">{{ item.file_size_mb }} MB</span>
                            {% else %}
                                <span class="file-size-bad">{{ item.file_size_bytes }} bytes</span>
                            {% endif %}
                        {% else %}
                            <span class="file-size-bad">missing</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if item.status == "saved" and item.is_playable %}
                        <div class="recording-action-links">
                            <a class="btn btn-primary btn-sm" href="/dashboard/camera-monitoring/recordings/{{ item.id }}">Watch in System</a>
                            <a class="btn btn-secondary btn-sm" href="/dashboard/camera-monitoring/recordings/{{ item.id }}/download">Download</a>
                        </div>
                        {% elif item.status == "saved" %}
                            <span class="file-size-bad">Broken / too small</span>
                        {% else %}
                            <span class="muted">Recording...</span>
                        {% endif %}
                    </td>''',
    )

save_file(index_path, index_text)

# Update playback template with playable warning
playback_path = "app/templates/camera_monitoring/playback.html"
playback_text = read_file(playback_path)

if "recording.is_playable" not in playback_text:
    playback_text = playback_text.replace(
        '''<div class="recording-player-wrap">
        <video class="recording-player" controls preload="metadata">
            <source src="{{ recording.file_path }}" type="video/mp4">
            Your browser does not support video playback.
        </video>
    </div>''',
        '''{% if recording.is_playable %}
    <div class="recording-player-wrap">
        <video class="recording-player" controls preload="metadata">
            <source src="{{ recording.file_path }}" type="video/mp4">
            Your browser does not support video playback.
        </video>
    </div>
    {% else %}
    <div class="broken-recording-warning">
        <strong>This recording file is too small or missing.</strong>
        <p>
            File size: {{ recording.file_size_bytes }} bytes.
            This usually means it was created before the recording reliability fix.
            Please record a new video.
        </p>
    </div>
    {% endif %}''',
    )

if "File Size" not in playback_text:
    playback_text = playback_text.replace(
        '''<div>
            <span class="muted">Duration</span>
            <strong>{{ "%.1f"|format(recording.duration_seconds) if recording.duration_seconds is not none else "-" }}s</strong>
        </div>''',
        '''<div>
            <span class="muted">Duration</span>
            <strong>{{ "%.1f"|format(recording.duration_seconds) if recording.duration_seconds is not none else "-" }}s</strong>
        </div>
        <div>
            <span class="muted">File Size</span>
            <strong>{{ recording.file_size_mb }} MB</strong>
        </div>''',
    )

playback_text = playback_text.replace(
    '''<a class="btn btn-primary" href="{{ recording.file_path }}" target="_blank">Open Raw Video</a>
        <a class="btn btn-secondary" href="/dashboard/camera-monitoring/recordings/{{ recording.id }}/download">Download Video</a>''',
    '''{% if recording.is_playable %}
        <a class="btn btn-primary" href="{{ recording.file_path }}" target="_blank">Open Raw Video</a>
        <a class="btn btn-secondary" href="/dashboard/camera-monitoring/recordings/{{ recording.id }}/download">Download Video</a>
        {% else %}
        <a class="btn btn-primary" href="/dashboard/camera-monitoring?session_id={{ recording.session_id }}">Record New Video</a>
        {% endif %}''',
)

save_file(playback_path, playback_text)

# CSS
css_path = "app/static/css/styles.css"
css_text = read_file(css_path)

if "Phase 9.3 Recording Polish" not in css_text:
    css_text += r"""

/* Phase 9.3 Recording Polish */
.file-size-good {
    display: inline-block;
    background: #ecfdf5;
    color: #047857;
    border: 1px solid #bbf7d0;
    border-radius: 999px;
    padding: 0.25rem 0.6rem;
    font-weight: 700;
}

.file-size-bad {
    display: inline-block;
    background: #fef2f2;
    color: #b91c1c;
    border: 1px solid #fecaca;
    border-radius: 999px;
    padding: 0.25rem 0.6rem;
    font-weight: 700;
}

.broken-recording-warning {
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #7f1d1d;
    border-radius: 1rem;
    padding: 1rem 1.25rem;
    margin: 1rem 0;
}
"""
    save_file(css_path, css_text)

# Docs
write_file("docs/recording_playback_polish.md", r"""
# Recording Playback Polish

## Issue

Some old recordings may be broken because they were created before the recording reliability fix.  
Broken recordings may be only a few hundred bytes and cannot play correctly.

## Product Fix

The recording table now shows:

- File size
- Watch in System button
- Download button
- Broken / too small warning

The playback page now warns the teacher if a recording is too small or missing.
""")

print("")
print("DONE: Phase 9.3 Recording Playback Polish applied.")
