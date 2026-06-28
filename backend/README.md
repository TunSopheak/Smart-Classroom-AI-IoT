# Backend README

This backend uses:

- FastAPI for API and dashboard routes
- SQLAlchemy for ORM models
- SQLite for local development database
- Pydantic for validation schemas
- Jinja2 for server-rendered teacher dashboard pages

## Run locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Main URLs

- `/dashboard` - teacher dashboard overview
- `/dashboard/students` - student management page
- `/dashboard/sessions` - session management page
- `/dashboard/sessions/{session_id}/attendance` - attendance records page
- `/docs` - FastAPI Swagger docs

## Notes

Phase 0 + 1 focuses on correct architecture and database design. QR scan, face recognition, and IoT automation are prepared but not fully implemented yet.
