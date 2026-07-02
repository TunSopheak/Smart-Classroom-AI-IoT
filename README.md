# Smart Classroom with AI Monitoring - IoT Project

Smart Classroom with AI Monitoring is a FastAPI and Jinja2 web dashboard for a final-year IoT project demo. It helps a teacher manage classroom sessions, record attendance, use face recognition as an attendance method, use QR attendance as a backup, and monitor classroom activity with AI/object detection features.

This repository is prepared as an MVP/final demo version for presentation and portfolio showcase. It is designed for local or LAN demonstration, especially with a Raspberry Pi 5 target device. It is not a cloud production deployment.

## Project Scope

This project is an MVP/final demo version of a Smart Classroom with AI Monitoring system. It focuses on FACE attendance, QR attendance backup, AI monitoring dashboard, phone/book/person detection, attendance reports, and mobile responsive LAN demo.

Public production deployment requires additional security, HTTPS, database migration, authentication hardening, and privacy review.

## Key Features

- Teacher dashboard for classroom overview and session control
- Student management with QR code generation
- Attendance records per class session
- QR attendance backup for low-light or untrained face cases
- OpenCV LBPH face recognition attendance workflow
- Face training page for demo dataset preparation
- Monitoring workspace for camera, face attendance, behavior checks, and object detection
- YOLO/object detection support for person, phone, and book detection
- Attendance and monitoring report pages with CSV export support
- Product settings, system health, privacy, and storage admin pages
- Mobile responsive dashboard for laptop, tablet, and phone presentation
- LAN demo support for devices connected to the same classroom network

## Tech Stack

- Backend: Python, FastAPI, Uvicorn
- Templates/UI: Jinja2, HTML, CSS, JavaScript
- Database: SQLite, SQLAlchemy ORM
- AI/Computer Vision: OpenCV, LBPH face recognition, Haar Cascade, YOLO/object detection
- Attendance: QR code backup and face recognition attendance
- Target hardware: Raspberry Pi 5, camera, optional ESP32/sensors/relay modules

## System Architecture Summary

The project uses a layered MVP architecture:

1. Device layer: laptop or Raspberry Pi 5 camera, optional ESP32 sensors, and optional relay devices.
2. AI layer: OpenCV face recognition and object detection services process camera input.
3. Backend layer: FastAPI routes, services, SQLAlchemy models, and SQLite storage.
4. Dashboard layer: Jinja2 pages provide teacher-facing controls and reports.
5. Data layer: local SQLite database, local face datasets, local trained models, recordings, and generated media.

For the final demo, the recommended setup is local or LAN mode. Public deployment would require stronger authentication, HTTPS, secret management, privacy controls, and production-grade storage.

## Demo Pages

Run the backend, then open:

```text
http://127.0.0.1:8000/dashboard
http://127.0.0.1:8000/dashboard/monitoring-workspace
http://127.0.0.1:8000/dashboard/face-training
http://127.0.0.1:8000/dashboard/reports
```

Other useful demo pages:

```text
http://127.0.0.1:8000/login
http://127.0.0.1:8000/dashboard/product-center
http://127.0.0.1:8000/dashboard/qr-attendance
http://127.0.0.1:8000/dashboard/final-demo
http://127.0.0.1:8000/dashboard/privacy
http://127.0.0.1:8000/dashboard/system-health
http://127.0.0.1:8000/docs
```

Demo accounts, if seeded in the local database:

```text
admin / admin123
teacher / teacher123
viewer / viewer123
```

## Local Setup

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-ai.txt
$env:SMART_CLASSROOM_DEVICE_API_KEY="smart-classroom-demo-device-key"
python -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/dashboard
```

See [docs/setup-local.md](docs/setup-local.md) for more setup notes.

## LAN Demo Commands

Use LAN mode when presenting from one host device and opening the dashboard from another device on the same Wi-Fi/network.

```powershell
cd backend
$env:SMART_CLASSROOM_DEVICE_API_KEY="smart-classroom-demo-device-key"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open this URL from another device on the same LAN, replacing `<host-ip>` with the laptop or Raspberry Pi IP address:

```text
http://<host-ip>:8000/dashboard
```

LAN demo is recommended for presentation because it keeps the project local while still showing multi-device access.

## Project Folder Structure

```text
smart-classroom-ai-iot/
  backend/
    app/
      core/          App settings, auth, security helpers
      crud/          Database access helpers
      database/      SQLite connection, migrations, seed data
      models/        SQLAlchemy models
      routers/       FastAPI API and dashboard routes
      schemas/       Pydantic schemas
      services/      Attendance, AI, IoT, dashboard services
      static/        CSS, JavaScript, generated local media
      templates/     Jinja2 dashboard pages
      main.py        FastAPI application entry point
    ai_module/
      face_recognition/
      object_detection/
    requirements.txt
    requirements-ai.txt
  ai_module/         Top-level AI notes and module documentation
  docs/              Demo, setup, architecture, features, privacy docs
  hardware/          Hardware planning notes
  mobile_app/        Mobile app placeholder/planning notes
  tests/             Repository structure tests
```

## Documentation

- [Demo guide](docs/demo-guide.md)
- [Local setup](docs/setup-local.md)
- [Architecture](docs/architecture.md)
- [Features](docs/features.md)
- [Privacy and security](docs/privacy-security.md)
- [Final demo checklist](docs/final-demo-checklist.md)

## Final Release

Final demo release tag:

- [v1.0-final-demo](https://github.com/TunSopheak/Smart-Classroom-AI-IoT/releases/tag/v1.0-final-demo)

This release represents the final MVP/demo checkpoint for portfolio sharing and presentation. It should not be described as a production cloud release.

## Privacy and Security Note

This project uses local demo data. Face datasets, trained face models, recordings, generated QR/media, and the SQLite database may contain private or sensitive information.

Do not commit:

- `.env`
- `smart_classroom.db`
- dataset images
- trained models
- recordings
- private face data
- generated QR/media if sensitive

Face data is stored locally for the MVP demo. Before any public or production deployment, the system needs stronger security controls, clear consent handling, access control review, encrypted transport, backup policies, and a privacy review.

## Team Members

M4-Y3, Group 1

- Thon Serey Rothana
- Tep Makhon
- Tit Sokhom
- Theam VanTim
- Tun Sopheak
- Hean Senghorn
- Chork Panha
- Say Menghorng
- Hoeun Sithai
- Heang Bunleab

## Team Contribution Summary

The project was completed through teamwork, including planning, backend development, dashboard UI, face recognition testing, dataset preparation, IoT concept design, documentation, and final demo preparation.

## Project Context

Project: Smart Classroom with AI Monitoring - IoT Project

Context: Student IoT/software engineering project for final demo and portfolio showcase

The project demonstrates how classroom attendance, AI camera monitoring, and IoT automation ideas can be integrated into one teacher-friendly dashboard.

## Current Status

- MVP/final demo version
- Local FastAPI/Jinja2 dashboard is available
- SQLite local database is used for demo storage
- Face recognition and QR attendance workflows are implemented for demonstration
- Object detection and monitoring workspace are available for demo scenarios
- LAN demo is supported and recommended for presentation
- Final demo release tag is available as `v1.0-final-demo`
- Cloud production deployment is not claimed as ready

## Future Improvements

- Improve production authentication and authorization
- Add HTTPS and secure deployment configuration
- Add stronger privacy controls and consent workflow
- Improve face model quality and anti-spoofing checks
- Add more robust Raspberry Pi camera integration
- Add MQTT/WebSocket support for real IoT devices
- Add backup and restore tools for demo data
- Add automated tests for key attendance and monitoring workflows
- Add a mobile app or PWA experience for teachers
