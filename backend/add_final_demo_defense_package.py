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

write_file("app/templates/demo/final_demo.html", r"""
{% extends "base.html" %}

{% block title %}Final Demo{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <p class="eyebrow">Phase 8.1 Final Demo</p>
        <h1>Final Demo & Project Defense Package</h1>
        <p>Use this page to guide your teacher presentation and final project defense.</p>
    </div>
    <a class="btn btn-secondary" href="/dashboard">Back Dashboard</a>
</div>

<div class="final-demo-note">
    <strong>Presentation Goal:</strong>
    Explain how Smart Classroom combines Attendance + AI Monitoring + IoT Automation + Reports into one teacher-friendly platform.
</div>

<div class="card">
    <h2>Demo Flow Checklist</h2>
    <p class="muted">Follow this order during your presentation.</p>

    <div class="demo-flow-grid">
        {% for item in demo_sections %}
        <div class="demo-step-card">
            <h3>{{ item.title }}</h3>
            <p>{{ item.goal }}</p>
            <a class="btn btn-primary btn-sm" href="{{ item.url }}">Open</a>
        </div>
        {% endfor %}
    </div>
</div>

<div class="card">
    <h2>System Architecture</h2>

    <div class="architecture-flow">
        <div class="architecture-node">Teacher Dashboard</div>
        <div class="architecture-arrow">→</div>
        <div class="architecture-node">FastAPI Backend</div>
        <div class="architecture-arrow">→</div>
        <div class="architecture-node">SQLite Database</div>
    </div>

    <div class="architecture-flow">
        <div class="architecture-node">QR Scanner</div>
        <div class="architecture-arrow">→</div>
        <div class="architecture-node">Attendance Service</div>
        <div class="architecture-arrow">→</div>
        <div class="architecture-node">Attendance Record + Event Log</div>
    </div>

    <div class="architecture-flow">
        <div class="architecture-node">OpenCV Camera</div>
        <div class="architecture-arrow">→</div>
        <div class="architecture-node">Face Recognition</div>
        <div class="architecture-arrow">→</div>
        <div class="architecture-node">FACE Attendance</div>
    </div>

    <div class="architecture-flow">
        <div class="architecture-node">ESP32 / Raspberry Pi</div>
        <div class="architecture-arrow">→</div>
        <div class="architecture-node">IoT API</div>
        <div class="architecture-arrow">→</div>
        <div class="architecture-node">Sensor + Automation Logs</div>
    </div>
</div>

<div class="card">
    <h2>Completed Features</h2>

    <div class="feature-grid">
        {% for feature in project_features %}
        <div class="feature-pill">✅ {{ feature }}</div>
        {% endfor %}
    </div>
</div>

<div class="card">
    <h2>Clean Presentation Script</h2>

    <div class="script-box clean-script">
        <div class="script-section">
            <h3>Opening</h3>
            <p>
                Good morning/afternoon teacher. Our project is called
                <strong>Smart Classroom with AI Monitoring</strong>.
                The goal is to help teachers manage classroom attendance, monitor student behavior,
                and control IoT devices in a smarter way.
            </p>
        </div>

        <div class="script-section">
            <h3>Problem</h3>
            <p>
                In a normal classroom, teachers need to check attendance manually, observe whether students
                are paying attention, and manage classroom devices such as lights and fans.
                These tasks take time and are difficult to track accurately.
            </p>
        </div>

        <div class="script-section">
            <h3>Solution</h3>
            <p>
                Our system combines QR attendance, face recognition attendance, AI monitoring,
                IoT sensor monitoring, automatic light/fan control, and report export in one dashboard.
            </p>
        </div>

        <div class="script-section">
            <h3>Closing</h3>
            <p>
                This project is still an MVP, but it has a clean architecture and is ready for future
                integration with Raspberry Pi, ESP32, Flutter mobile app, and real AI models like YOLO or MediaPipe.
            </p>
        </div>
    </div>
</div>

<div class="card">
    <h2>Defense Q&A</h2>

    <div class="qa-list">
        {% for item in defense_points %}
        <div class="qa-item">
            <h3>{{ item.question }}</h3>
            <p>{{ item.answer }}</p>
        </div>
        {% endfor %}
    </div>
</div>

<div class="card">
    <h2>Final Demo Commands</h2>

    <pre class="code-block">cd "D:\IT\IT-RUPP\Y3\CN\Project\smart-classroom-ai-iot\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

Open:
http://127.0.0.1:8000/dashboard/final-demo</pre>
</div>
{% endblock %}
""")

write_file("docs/final_demo_checklist.md", r"""
# Final Demo Checklist

## Before Demo

- Open PowerShell in the backend folder
- Start FastAPI server
- Open the final demo page
- Prepare camera for face recognition
- Make sure session #7 or latest session is available
- Make sure IoT demo devices exist
- Make sure report page has data

## Start Server

```powershell
cd "D:\IT\IT-RUPP\Y3\CN\Project\smart-classroom-ai-iot\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/dashboard/final-demo
```

## Demo Order

1. Final Demo page
2. Dashboard overview
3. Students and QR cards
4. Face profile
5. Sessions and attendance
6. Face recognition attendance
7. AI Monitoring
8. IoT Monitoring
9. Auto light/fan off rule
10. Reports and CSV export

## Important Demo Proof

Show these clearly:

- S001 attendance method = FACE
- Confidence is saved
- AI event is linked to S001
- IoT sensor readings are shown
- Light/fan control works
- Auto-off rule logs executed/skipped
- Reports page summarizes all data

## Backup Plan

If camera does not work during demo:

- Use existing face attendance record
- Explain the OpenCV workflow
- Show Face Profile sample count
- Show Attendance Event Log with FACE method

If QR scan is not available:

- Paste QR value manually: `SC-STUDENT-S001`

If IoT hardware is not available:

- Use simulated IoT devices and sensor readings
- Explain that the API is ready for ESP32/Raspberry Pi integration
""")

write_file("docs/release_notes_v1.md", r"""
# Release Notes - v1.0 Final Demo

## Version

v1.0-final-demo

## Project

Smart Classroom with AI Monitoring - IoT Project

## Final Demo Features

### Attendance

- QR attendance
- Face recognition attendance
- Attendance status per class session
- Present / Late / Absent / Permission
- Manual override with reason
- Attendance event logging

### AI Monitoring

- Phone usage event
- Sleeping event
- Leaving seat event
- Hand raising event
- Attention low event
- Student-level AI event support
- AI event history and filters

### IoT Monitoring

- Raspberry Pi 5 controller simulation
- ESP32 node simulation
- DHT22 temperature/humidity sensor simulation
- Noise sensor simulation
- Motion sensor simulation
- Light relay control
- Fan relay control
- Sensor reading logs

### Automation

- Empty classroom auto-off rule
- Light/fan auto-off simulation
- Automation event history
- Executed/skipped automation status

### Reports

- Attendance report
- AI monitoring report
- IoT sensor report
- Automation report
- CSV export

### Final Demo

- Final demo guide page
- Project architecture explanation
- Defense Q&A
- Presentation script
- Demo checklist

## Current Limitations

- Face recognition uses LBPH prototype
- AI behavior monitoring is simulated
- IoT hardware is simulated
- SQLite is used for local demo
- Flutter mobile app is planned for future development

## Future Improvements

- Raspberry Pi 5 deployment
- ESP32 real sensor integration
- YOLO object detection
- MediaPipe pose detection
- Flutter mobile app
- Real-time dashboard with WebSocket
- PDF report export
""")

# Update README with release note
readme_text = read_file("../README.md")
if "## v1.0 Final Demo Release" not in readme_text:
    readme_text += r"""

## v1.0 Final Demo Release

Stable final demo tag:

```text
v1.0-final-demo
```

Final release documents:

```text
docs/final_demo_checklist.md
docs/release_notes_v1.md
docs/project_defense.md
docs/final_demo_script.md
```

Final demo page:

```text
http://127.0.0.1:8000/dashboard/final-demo
```
"""
    save_file("../README.md", readme_text)

# CSS polish
css_text = read_file("app/static/css/styles.css")
if "Phase 8.1 Final Script Polish" not in css_text:
    css_text += r"""

/* Phase 8.1 Final Script Polish */
.clean-script {
    display: grid;
    gap: 1rem;
}

.script-section {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 0.85rem;
    padding: 1rem;
}

.script-section h3 {
    margin: 0 0 0.5rem;
    font-size: 1.1rem;
    color: #0f172a;
}

.script-section p {
    margin: 0;
    line-height: 1.6;
}

.script-section strong {
    color: #1d4ed8;
    font-size: inherit;
}
"""
    save_file("app/static/css/styles.css", css_text)

print("")
print("DONE: Phase 8.1 Final Text Polish + Release Preparation applied.")
