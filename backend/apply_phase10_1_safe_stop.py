from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read_file(path):
    return (ROOT / path).read_text(encoding="utf-8")

def save_file(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")
    print(f"Updated: {path}")

def replace_block(text, start_marker, end_marker, new_block):
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[:start] + new_block.rstrip() + "\n\n" + text[end:]

# 1) Patch camera service: add recording lock
service_path = "app/services/camera_monitoring_service.py"
service = read_file(service_path)

if "self.record_lock = threading.Lock()" not in service:
    service = service.replace(
        "self.lock = threading.Lock()",
        "self.lock = threading.Lock()\n        self.record_lock = threading.Lock()",
        1,
    )

old_write = '''            if self.recording and self.video_writer is not None:
                try:
                    self.video_writer.write(annotated)
                except Exception as exc:
                    print(f"Recording write error: {exc}")'''

new_write = '''            with self.record_lock:
                if self.recording and self.video_writer is not None:
                    try:
                        self.video_writer.write(annotated)
                    except Exception as exc:
                        print(f"Recording write error: {exc}")'''

if old_write in service:
    service = service.replace(old_write, new_write, 1)

new_stop_recording = r'''
    def stop_recording(self):
        with self.record_lock:
            if not self.recording and self.video_writer is None:
                return None

            stopped_at = datetime.utcnow()
            started_at = self.recording_started_at
            path = self.recording_path
            filename = path.name if path else None
            writer = self.video_writer

            self.recording = False
            self.video_writer = None
            self.recording_path = None
            self.recording_started_at = None

        duration = None
        if started_at:
            duration = (stopped_at - started_at).total_seconds()

        if writer:
            try:
                writer.release()
            except Exception as exc:
                print(f"VideoWriter release warning: {exc}")

        result = {
            "path": str(path) if path else None,
            "filename": filename,
            "started_at": started_at,
            "stopped_at": stopped_at,
            "duration_seconds": duration,
        }

        if path and path.exists():
            print(f"Recording saved: {path}")
            print(f"Recording size: {path.stat().st_size} bytes")

        return result
'''

service = replace_block(
    service,
    "    def stop_recording(self):",
    "    def get_status(self):",
    new_stop_recording,
)

save_file(service_path, service)

# 2) Patch router: make stop route safe and add fix-stuck route
router_path = "app/routers/camera_monitoring_router.py"
router = read_file(router_path)

new_stop_route = r'''
@router.post("/dashboard/camera-monitoring/record/stop")
def dashboard_stop_recording(
    session_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    result = None

    try:
        result = camera_service.stop_recording()
    except Exception as exc:
        print(f"Safe stop caught recording error: {exc}")

    if result and result.get("filename"):
        recording = (
            db.query(CameraRecording)
            .filter(CameraRecording.filename == result["filename"])
            .order_by(CameraRecording.started_at.desc())
            .first()
        )

        if recording:
            recording.status = "saved"
            recording.stopped_at = result["stopped_at"]
            recording.duration_seconds = result["duration_seconds"]
            db.commit()
    else:
        # Recovery fallback: if stop crashed after file was written,
        # mark the latest valid recording as saved.
        latest = (
            db.query(CameraRecording)
            .filter(CameraRecording.status == "recording")
            .order_by(CameraRecording.started_at.desc())
            .first()
        )

        if latest:
            file_path = get_recording_file_path(latest)
            if file_path.exists() and file_path.stat().st_size > 100000:
                latest.status = "saved"
                latest.stopped_at = datetime.utcnow()
                if latest.started_at:
                    latest.duration_seconds = (latest.stopped_at - latest.started_at).total_seconds()
                db.commit()

    url = "/dashboard/camera-monitoring"
    if session_id:
        url += f"?session_id={session_id}"
    return RedirectResponse(url=url, status_code=303)
'''

router = replace_block(
    router,
    '@router.post("/dashboard/camera-monitoring/record/stop")',
    '@router.post("/dashboard/camera-monitoring/behavior")',
    new_stop_route,
)

if '@router.post("/dashboard/camera-monitoring/recordings/fix-stuck")' not in router:
    fix_route = r'''

@router.post("/dashboard/camera-monitoring/recordings/fix-stuck")
def dashboard_fix_stuck_recordings(
    session_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    stuck_recordings = (
        db.query(CameraRecording)
        .filter(CameraRecording.status == "recording")
        .order_by(CameraRecording.started_at.desc())
        .all()
    )

    fixed_count = 0

    for item in stuck_recordings:
        file_path = get_recording_file_path(item)

        if file_path.exists() and file_path.stat().st_size > 100000:
            item.status = "saved"
            item.stopped_at = datetime.utcnow()
            if item.started_at:
                item.duration_seconds = (item.stopped_at - item.started_at).total_seconds()
            fixed_count += 1

    db.commit()
    print(f"Fixed stuck recordings: {fixed_count}")

    url = "/dashboard/camera-monitoring"
    if session_id:
        url += f"?session_id={session_id}"
    return RedirectResponse(url=url, status_code=303)
'''
    router = router.replace(
        '@router.get("/dashboard/camera-monitoring/recordings/{recording_id}")',
        fix_route + '\n\n@router.get("/dashboard/camera-monitoring/recordings/{recording_id}")',
        1,
    )

save_file(router_path, router)

# 3) Add Fix Stuck button in template
template_path = "app/templates/camera_monitoring/index.html"
template = read_file(template_path)

if "Fix Stuck Recordings" not in template:
    template = template.replace(
        "<h2>Recording History</h2>",
        '''<div class="section-title-row">
        <h2>Recording History</h2>
        <form method="post" action="/dashboard/camera-monitoring/recordings/fix-stuck">
            <input type="hidden" name="session_id" value="{{ selected_session.id if selected_session else '' }}">
            <button class="btn btn-warning btn-sm" type="submit">Fix Stuck Recordings</button>
        </form>
    </div>''',
        1,
    )

save_file(template_path, template)

# 4) CSS
css_path = "app/static/css/styles.css"
css = read_file(css_path)

if "Phase 10.1 Safe Recording Stop" not in css:
    css += r"""

/* Phase 10.1 Safe Recording Stop */
.section-title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
}
"""
    save_file(css_path, css)

print("")
print("DONE: Phase 10.1 Safe Recording Stop patch applied.")
