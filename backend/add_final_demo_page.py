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

write_file("app/routers/demo_router.py", r"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Final Demo"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard/final-demo")
def final_demo_page(request: Request):
    demo_sections = [
        {
            "title": "1. Dashboard Overview",
            "goal": "Show total students, attendance summary, active session, and system status.",
            "url": "/dashboard",
        },
        {
            "title": "2. Student & QR Management",
            "goal": "Show student list, QR cards, printable QR, and face profile.",
            "url": "/dashboard/students",
        },
        {
            "title": "3. Session & Attendance",
            "goal": "Show session control, QR attendance, face attendance, manual override, and event logs.",
            "url": "/dashboard/sessions",
        },
        {
            "title": "4. AI Monitoring",
            "goal": "Show phone usage, sleeping, leaving seat, hand raising, attention low, and student-level AI events.",
            "url": "/dashboard/ai-monitoring",
        },
        {
            "title": "5. IoT Monitoring",
            "goal": "Show Raspberry Pi / ESP32 devices, sensor readings, light/fan control, and auto-off rule.",
            "url": "/dashboard/iot-monitoring",
        },
        {
            "title": "6. Reports & Export",
            "goal": "Show attendance report, AI report, IoT report, automation report, and CSV export.",
            "url": "/dashboard/reports",
        },
    ]

    project_features = [
        "Student management",
        "QR attendance",
        "Face recognition attendance",
        "Attendance event logging",
        "Teacher manual override",
        "AI behavior monitoring",
        "Student-level AI event logging",
        "IoT device and sensor monitoring",
        "Light/fan control simulation",
        "Auto light/fan off rule",
        "Reports and CSV export",
    ]

    defense_points = [
        {
            "question": "Why is attendance not stored directly in the Student table?",
            "answer": "Because attendance changes per class session. A student can be present in one session and absent in another, so attendance must be stored in AttendanceRecord linked to session and student.",
        },
        {
            "question": "Why do we keep event logs?",
            "answer": "Event logs make the system reliable and auditable. Every QR scan, face recognition result, AI event, and automation decision can be reviewed later.",
        },
        {
            "question": "How does face recognition connect with attendance?",
            "answer": "OpenCV recognizes a student ID, then sends it to FastAPI. FastAPI updates attendance using the same attendance workflow and logs the event as FACE.",
        },
        {
            "question": "How does IoT automation work?",
            "answer": "The system checks classroom occupancy from attendance records. If no students are detected for 5 minutes, the system can turn off lights and fans.",
        },
        {
            "question": "What makes this project scalable?",
            "answer": "The system separates models, routers, schemas, services, templates, AI modules, IoT APIs, and reports. This makes future Flutter app, Raspberry Pi, ESP32, YOLO, or MediaPipe integration easier.",
        },
    ]

    return templates.TemplateResponse(
        request,
        "demo/final_demo.html",
        {
            "request": request,
            "demo_sections": demo_sections,
            "project_features": project_features,
            "defense_points": defense_points,
        },
    )
""")

write_file("app/templates/demo/final_demo.html", r"""
{% extends "base.html" %}

{% block title %}Final Demo{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <p class="eyebrow">Phase 8 Final Demo</p>
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
    <h2>Presentation Script</h2>

    <div class="script-box">
        <p><strong>Opening:</strong></p>
        <p>
            Good morning/afternoon teacher. Our project is called <strong>Smart Classroom with AI Monitoring</strong>.
            The goal is to help teachers manage classroom attendance, monitor student behavior, and control IoT devices in a smarter way.
        </p>

        <p><strong>Problem:</strong></p>
        <p>
            In a normal classroom, teachers need to check attendance manually, observe whether students are paying attention,
            and manage classroom devices such as lights and fans. These tasks take time and are difficult to track accurately.
        </p>

        <p><strong>Solution:</strong></p>
        <p>
            Our system combines QR attendance, face recognition attendance, AI monitoring, IoT sensor monitoring,
            automatic light/fan control, and report export in one dashboard.
        </p>

        <p><strong>Closing:</strong></p>
        <p>
            This project is still an MVP, but it has a clean architecture and is ready for future integration with Raspberry Pi,
            ESP32, Flutter mobile app, and real AI models like YOLO or MediaPipe.
        </p>
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

write_file("docs/project_defense.md", r"""
# Smart Classroom AI IoT - Project Defense Guide

## Project Title

Smart Classroom with AI Monitoring

## Main Idea

This project helps teachers manage classroom attendance, monitor student behavior, control IoT devices, and export reports using one web dashboard.

## Problem Statement

In a normal classroom, teachers spend time on:

- Manual attendance checking
- Monitoring student attention
- Checking classroom environment
- Managing lights and fans
- Preparing attendance reports manually

This system reduces those manual tasks by combining AI, IoT, and web technology.

## Proposed Solution

The system provides:

- QR attendance
- Face recognition attendance
- AI behavior monitoring
- IoT device and sensor monitoring
- Auto light/fan off rule
- Attendance and event reports
- CSV export

## System Modules

### 1. Student Management

Teachers can manage students and generate QR codes.

### 2. Session Management

Attendance is linked to each class session.

### 3. Attendance

The system supports:

- P = Present
- L = Late
- A = Absent
- Pm = Permission

### 4. Face Recognition

OpenCV is used to capture, train, and recognize student faces.

### 5. AI Monitoring

The system logs classroom behavior events:

- Phone usage
- Sleeping
- Leaving seat
- Hand raising
- Attention low

### 6. IoT Monitoring

The system simulates Raspberry Pi and ESP32 devices:

- Temperature
- Humidity
- Noise
- Light level
- Light relay
- Fan relay
- Camera module

### 7. Automation

If no students are detected for 5 minutes, the system can automatically turn off lights and fans.

### 8. Reports

Teachers can review and export:

- Attendance report
- AI event report
- IoT sensor report
- Automation report

## Architecture

Teacher Dashboard -> FastAPI Backend -> SQLite Database

QR Scanner -> Attendance Service -> Attendance Record + Event Log

OpenCV Camera -> Face Recognition -> FastAPI Attendance API

ESP32 / Raspberry Pi -> IoT API -> Sensor Readings + Automation Rule

## Why Attendance Is Not Stored in Student Table

Attendance changes by session. A student may be present in one session and absent in another. Therefore, attendance must be stored in a separate AttendanceRecord table linked to student and session.

## Future Improvements

- Flutter mobile app
- Real Raspberry Pi 5 deployment
- ESP32 real sensor integration
- YOLO object detection
- MediaPipe pose detection
- Real-time WebSocket dashboard
- PDF report export
""")

write_file("docs/final_demo_script.md", r"""
# Final Demo Script

## Opening

Good morning/afternoon teacher.  
Our project is called **Smart Classroom with AI Monitoring**.

The purpose of this project is to help teachers manage classroom attendance, monitor student behavior, and control classroom IoT devices in a smarter and more modern way.

## Problem

Normally, teachers need to:

1. Check attendance manually
2. Monitor whether students are paying attention
3. Check classroom environment
4. Control lights and fans manually
5. Prepare reports manually

These tasks take time and are difficult to track accurately.

## Solution

Our system combines:

1. QR attendance
2. Face recognition attendance
3. AI behavior monitoring
4. IoT sensor monitoring
5. Automatic light/fan control
6. Reports and CSV export

## Demo Flow

### Step 1: Dashboard

Show the main dashboard and explain the summary cards.

### Step 2: Students

Show student list, QR code, QR print, and face profile.

### Step 3: Attendance Session

Show session attendance page. Demonstrate QR or face attendance.

### Step 4: Face Recognition

Run OpenCV recognition and show that the attendance method becomes FACE.

### Step 5: AI Monitoring

Show AI events such as phone usage, sleeping, leaving seat, hand raising, and attention low.

### Step 6: IoT Monitoring

Show device list, sensor readings, light/fan control, and automation rule.

### Step 7: Reports

Show attendance report, AI report, IoT report, automation report, and CSV export.

## Closing

This project is still an MVP, but the architecture is clean and ready for future development.  
In the future, we can connect the system with Raspberry Pi 5, ESP32 sensors, Flutter mobile app, YOLO object detection, and MediaPipe pose detection.

Thank you.
""")

# Update main.py
main_text = read_file("app/main.py")
if "phase8_demo_router" not in main_text:
    main_text += """

# Phase 8 Final Demo routes
from app.routers.demo_router import router as phase8_demo_router
app.include_router(phase8_demo_router)
"""
    save_file("app/main.py", main_text)

# Update base navigation
base_text = read_file("app/templates/base.html")
if "/dashboard/final-demo" not in base_text:
    if "/dashboard/reports" in base_text:
        base_text = base_text.replace(
            '<a href="/dashboard/reports">Reports</a>',
            '<a href="/dashboard/reports">Reports</a>\n    <a href="/dashboard/final-demo">Final Demo</a>',
            1,
        )
    elif "</nav>" in base_text:
        base_text = base_text.replace(
            "</nav>",
            '    <a href="/dashboard/final-demo">Final Demo</a>\n</nav>',
            1,
        )
    save_file("app/templates/base.html", base_text)

# Update README
readme_text = read_file("../README.md")
if "## Final Demo" not in readme_text:
    readme_text += r"""

## Final Demo

Final demo guide page:

```text
http://127.0.0.1:8000/dashboard/final-demo
```

The final demo package includes:

- Demo checklist
- System architecture explanation
- Project defense talking points
- Demo script
- Teacher Q&A preparation

Related documents:

```text
docs/project_defense.md
docs/final_demo_script.md
```
"""
    save_file("../README.md", readme_text)

# CSS
css_text = read_file("app/static/css/styles.css")
if "Phase 8 Final Demo" not in css_text:
    css_text += r"""

/* Phase 8 Final Demo */
.final-demo-note {
    background: #f5f3ff;
    border: 1px solid #ddd6fe;
    color: #3b0764;
    padding: 1rem 1.25rem;
    border-radius: 1rem;
    margin: 1rem 0 1.5rem;
}

.demo-flow-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1rem;
}

.demo-step-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 1rem;
    padding: 1rem;
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.05);
}

.demo-step-card h3 {
    margin-bottom: 0.5rem;
}

.architecture-flow {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 0.9rem 0;
    flex-wrap: wrap;
}

.architecture-node {
    background: #eef2ff;
    border: 1px solid #c7d2fe;
    color: #312e81;
    border-radius: 999px;
    padding: 0.65rem 1rem;
    font-weight: 800;
}

.architecture-arrow {
    font-weight: 900;
    color: #2563eb;
}

.feature-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
}

.feature-pill {
    background: #ecfdf5;
    border: 1px solid #bbf7d0;
    color: #047857;
    border-radius: 999px;
    padding: 0.55rem 0.9rem;
    font-weight: 700;
}

.script-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 1rem;
    padding: 1rem 1.25rem;
}

.qa-list {
    display: grid;
    gap: 1rem;
}

.qa-item {
    border-left: 4px solid #2563eb;
    background: #f8fafc;
    padding: 1rem;
    border-radius: 0.75rem;
}

@media (max-width: 1000px) {
    .demo-flow-grid {
        grid-template-columns: 1fr 1fr;
    }
}

@media (max-width: 700px) {
    .demo-flow-grid {
        grid-template-columns: 1fr;
    }
}
"""
    save_file("app/static/css/styles.css", css_text)

print("")
print("DONE: Phase 8 Final Demo Polish & Project Defense Package applied.")
