# Smart Classroom AI IoT

A modern Smart Classroom platform for teachers to manage students, class sessions, QR attendance, face recognition attendance, and future AI/IoT monitoring.

This project was rebuilt from scratch as a clean MVP for the Smart Classroom with AI Monitoring - IoT Project.

## Current Status

- Phase 0 + 1: Project setup, database, dashboard
- Phase 2: QR attendance and event logging
- Phase 2.1: Teacher session control UI
- Phase 3: Student management and QR images
- Phase 3.1: Print/export QR workflow
- Phase 4: Face profile and face simulation
- Phase 4.1: Real OpenCV webcam face recognition
- Phase 4.2: Clean webcam-to-FastAPI attendance workflow

## Main Features

### Student Management

- Add, edit, activate, and deactivate students
- Generate QR code values and QR images
- Print one student QR card
- Print all student QR cards
- Export student QR list as CSV
- Store face dataset path per student

### Attendance Management

- Attendance is recorded per class session
- Attendance status is not stored in the Student table
- Supported status codes:
  - P = Present
  - L = Late
  - A = Absent
  - Pm = Permission
- Teacher can manually override status with reason
- Final attendance record stores method, confidence, first_seen_time, overridden_by, override_reason, and updated_at

### QR Attendance

- QR scan logs every event
- Unknown QR is logged
- Duplicate QR scan is logged
- Valid QR updates final attendance record
- First seen time is protected from duplicate overwrite

### Face Recognition Attendance

- Face dataset profile per student
- OpenCV webcam capture
- LBPH face training
- Real webcam recognition
- FastAPI attendance integration
- FACE attendance event logging
- Duplicate spam prevention
- Confidence score stored in attendance record

## Tech Stack

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy ORM
- SQLite
- Pydantic

### Dashboard

- Jinja2 templates
- HTML
- CSS
- JavaScript

### AI

- OpenCV
- OpenCV LBPH Face Recognizer
- Haar Cascade face detection

### Future IoT

- Raspberry Pi 5
- Pi Camera / USB Camera
- ESP32 / ESP32-CAM
- DHT22
- Noise sensor
- Relay module
- Fan/light automation

## Folder Structure

smart-classroom-ai-iot/
  backend/
    app/
      main.py
      core/
      crud/
      database/
      models/
      routers/
      schemas/
      services/
      templates/
      static/
    ai_module/
      face_recognition/
        capture_faces.py
        train_lbph.py
        recognize_face.py
        datasets/   ignored by Git
        models/     ignored by Git
    requirements.txt
    requirements-ai.txt
  docs/
  hardware/
  mobile_app/
  tests/

## Privacy Note

Face datasets and trained face models are ignored by Git.

Do not upload real student face data to GitHub.

Ignored paths:

- backend/ai_module/face_recognition/datasets/
- backend/ai_module/face_recognition/models/

## Setup

Clone repository:

git clone https://github.com/TunSopheak/Smart-Classroom-AI-IoT.git
cd Smart-Classroom-AI-IoT\backend

Create virtual environment:

python -m venv .venv
.venv\Scripts\Activate.ps1

Install backend requirements:

pip install -r requirements.txt

Install AI requirements:

pip install -r requirements-ai.txt

Run server:

uvicorn app.main:app --reload

Open dashboard:

http://127.0.0.1:8000/dashboard

## Demo Pages

Dashboard:
http://127.0.0.1:8000/dashboard

Students:
http://127.0.0.1:8000/dashboard/students

Sessions:
http://127.0.0.1:8000/dashboard/sessions

API Docs:
http://127.0.0.1:8000/docs

## Face Recognition Workflow

Capture face samples:

python ai_module\face_recognition\capture_faces.py --student-id S001 --samples 80

Train LBPH model:

python ai_module\face_recognition\train_lbph.py

Sync training metadata:

python sync_face_training.py

Test recognition only:

python ai_module\face_recognition\recognize_face.py --threshold 75

Send real face attendance to FastAPI:

python ai_module\face_recognition\recognize_face.py --session-id 7 --send-api --threshold 75

## QR Attendance Workflow

Example QR value:

SC-STUDENT-S001

Workflow:

1. Open session attendance page
2. Scan or paste QR value
3. System logs event
4. System updates attendance record
5. Duplicate scans are logged but do not overwrite first seen time

## Current Git Checkpoint

phase-4-2-face-recognition

## Next Phase

Phase 5 will add AI monitoring event logging:

- Phone usage
- Sleeping
- Leaving seat
- Attention level
- Hand raising
- Behavior event dashboard
- Future MediaPipe / YOLO integration

## Author

Tun Sopheak  
Computer Science Student, RUPP  
Project: Smart Classroom with AI Monitoring - IoT Project


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


## Phase 11 Product Settings and System Health

Product pages:

- http://127.0.0.1:8000/dashboard/product-settings
- http://127.0.0.1:8000/dashboard/system-health
- http://127.0.0.1:8000/api/system-health

This phase adds product-level settings, health checks, and product readiness verification.
