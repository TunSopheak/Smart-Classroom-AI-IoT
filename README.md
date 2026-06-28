# Smart Classroom with AI Monitoring - IoT Project

A clean restart of the Smart Classroom platform using FastAPI, SQLAlchemy, SQLite, Jinja2, and a modular architecture for future AI, IoT, and Flutter features.

## Current phase

This repository currently implements **Phase 0 + Phase 1**:

- Professional project structure
- FastAPI backend
- SQLite database using SQLAlchemy ORM
- Core database models
- Pydantic schemas
- Seed data for demo teacher, class, students, subject, and class session
- Basic Jinja2 dashboard layout
- API foundations for students, classes, subjects, sessions, and attendance records
- Placeholder modules for AI, IoT hardware, mobile app, docs, and tests

Advanced AI, real QR scanning, IoT automation, and Flutter are intentionally not implemented yet. They are planned for later phases after the core database and attendance workflow are stable.

## Quick start

```bash
cd backend
python -m venv .venv
```

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
uvicorn app.main:app --reload
```

Open:

- Dashboard: http://127.0.0.1:8000/dashboard
- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Demo data

The app creates tables and seed data automatically on startup for local development.

Demo account:

- Username: `admin`
- Password: `admin123` placeholder only; real login is not implemented yet.

Demo classroom:

- Class: `M4-Y3-G1`
- Subject: `IoT Project`
- Session: `Smart Classroom MVP Demo Session`

## Important design rule

Attendance status is **not stored inside the Student table**.

Student identity is stored in `students`.
Attendance result per session is stored in `attendance_records`.
Every QR or face recognition scan will later be logged in `attendance_events`.

## Phase roadmap

1. Phase 0: Setup and structure ✅
2. Phase 1: Core backend and database ✅
3. Phase 2: Attendance workflow and QR scanning
4. Phase 3: Dashboard MVP improvements
5. Phase 4: Face recognition prototype
6. Phase 5: AI monitoring prototype
7. Phase 6: IoT automation
8. Phase 7: Reports/export
9. Phase 8: Flutter mobile app
10. Phase 9: Final polish and presentation
