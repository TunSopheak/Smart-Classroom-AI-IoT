from pathlib import Path

path = Path("app/services/face_service.py")
text = path.read_text(encoding="utf-8")

if "confidence = round(float(confidence), 2)" not in text:
    text = text.replace(
        '''def simulate_face_attendance(
    db: Session,
    student_id: int,
    session_id: int | None = None,
    confidence: float = 0.86,
    raw_source: str = "dashboard_face_simulation",
    event_time: datetime | None = None,
) -> dict[str, Any]:
    session = db.get(ClassSession, session_id) if session_id else get_active_session(db)''',
        '''def simulate_face_attendance(
    db: Session,
    student_id: int,
    session_id: int | None = None,
    confidence: float = 0.86,
    raw_source: str = "dashboard_face_simulation",
    event_time: datetime | None = None,
) -> dict[str, Any]:
    confidence = round(float(confidence), 2)

    session = db.get(ClassSession, session_id) if session_id else get_active_session(db)'''
    )

path.write_text(text, encoding="utf-8")

print("Step 1 done: backend FACE confidence rounding added.")
