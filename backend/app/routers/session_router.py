from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.session_crud import create_session, get_session, get_sessions, update_session
from app.database.database import get_db
from app.models.classroom import Classroom
from app.models.class_session import ClassSession
from app.models.subject import Subject
from app.schemas.session_schema import ClassSessionCreate, ClassSessionRead, ClassSessionUpdate
from app.services.attendance_service import finalize_session_absences
from app.services.session_service import prepare_session_attendance

router = APIRouter(tags=["Class Sessions"])
templates = Jinja2Templates(directory="app/templates")


def close_other_active_sessions(db: Session, keep_session_id: int | None = None) -> None:
    """Keep teacher workflow simple: only one active session at a time."""
    query = db.query(ClassSession).filter(ClassSession.active.is_(True))
    if keep_session_id is not None:
        query = query.filter(ClassSession.id != keep_session_id)

    for session in query.all():
        session.active = False

    db.commit()


@router.get("/api/sessions", response_model=list[ClassSessionRead])
def api_list_sessions(db: Session = Depends(get_db)):
    return get_sessions(db)


@router.post("/api/sessions", response_model=ClassSessionRead)
def api_create_session(data: ClassSessionCreate, db: Session = Depends(get_db)):
    if data.active:
        close_other_active_sessions(db)

    session = create_session(db, data)
    prepare_session_attendance(db, session)
    return session


@router.get("/api/sessions/{session_id}", response_model=ClassSessionRead)
def api_get_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/api/sessions/{session_id}", response_model=ClassSessionRead)
def api_update_session(session_id: int, data: ClassSessionUpdate, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return update_session(db, session, data)


@router.post("/api/sessions/{session_id}/open", response_model=ClassSessionRead)
def api_open_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    close_other_active_sessions(db, keep_session_id=session.id)
    session.active = True
    db.commit()
    db.refresh(session)

    prepare_session_attendance(db, session)
    return session


@router.post("/api/sessions/{session_id}/close", response_model=ClassSessionRead)
def api_close_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return finalize_session_absences(db, session)


@router.get("/dashboard/sessions", response_class=HTMLResponse)
def dashboard_sessions(request: Request, db: Session = Depends(get_db)):
    active_session = (
        db.query(ClassSession)
        .filter(ClassSession.active.is_(True))
        .order_by(ClassSession.start_time.desc())
        .first()
    )

    return templates.TemplateResponse(
        request,
        "sessions/list.html",
        {
            "sessions": get_sessions(db),
            "classes": db.query(Classroom).order_by(Classroom.id).all(),
            "subjects": db.query(Subject).order_by(Subject.id).all(),
            "active_session": active_session,
        },
    )


@router.post("/dashboard/sessions/create")
def dashboard_create_session(
    classroom_id: int = Form(...),
    subject_id: int = Form(...),
    title: str = Form(...),
    db: Session = Depends(get_db),
):
    close_other_active_sessions(db)

    now = datetime.now().replace(microsecond=0)
    session = create_session(
        db,
        ClassSessionCreate(
            classroom_id=classroom_id,
            subject_id=subject_id,
            title=title,
            start_time=now,
            late_time=now + timedelta(minutes=15),
            close_time=now + timedelta(hours=2),
            active=True,
            created_by=1,
        ),
    )
    prepare_session_attendance(db, session)
    return RedirectResponse(url=f"/dashboard/sessions/{session.id}/attendance", status_code=303)


@router.post("/dashboard/sessions/{session_id}/open")
def dashboard_open_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    close_other_active_sessions(db, keep_session_id=session.id)
    session.active = True
    db.commit()
    db.refresh(session)

    prepare_session_attendance(db, session)
    return RedirectResponse(url="/dashboard/sessions", status_code=303)


@router.post("/dashboard/sessions/{session_id}/close")
def dashboard_close_session(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    finalize_session_absences(db, session)
    return RedirectResponse(url="/dashboard/sessions", status_code=303)
