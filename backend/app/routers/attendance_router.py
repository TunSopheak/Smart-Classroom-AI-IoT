from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.constants import AttendanceStatus
from app.crud.attendance_crud import get_attendance_events, get_attendance_record, get_attendance_records
from app.crud.session_crud import get_session
from app.database.database import get_db
from app.schemas.attendance_schema import (
    AttendanceOverrideRequest,
    AttendanceRecordRead,
    AttendanceScanResponse,
    QRScanRequest,
)
from app.services.attendance_service import (
    ensure_attendance_records_for_session,
    override_attendance_record,
    scan_qr_attendance,
)

router = APIRouter(tags=["Attendance"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/api/sessions/{session_id}/attendance", response_model=list[AttendanceRecordRead])
def api_get_session_attendance(session_id: int, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ensure_attendance_records_for_session(db, session)
    return get_attendance_records(db, session_id)


@router.post("/api/attendance/scan-qr", response_model=AttendanceScanResponse)
def api_scan_qr_attendance(data: QRScanRequest, db: Session = Depends(get_db)):
    try:
        return scan_qr_attendance(
            db=db,
            qr_code=data.qr_code,
            session_id=data.session_id,
            raw_source=data.raw_source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/api/attendance/{record_id}/override", response_model=AttendanceRecordRead)
def api_override_attendance(record_id: int, data: AttendanceOverrideRequest, db: Session = Depends(get_db)):
    record = get_attendance_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return override_attendance_record(
        db=db,
        record=record,
        status=data.status,
        overridden_by=data.overridden_by,
        reason=data.override_reason,
    )


@router.get("/api/sessions/{session_id}/events")
def api_get_session_events(session_id: int, db: Session = Depends(get_db)):
    return get_attendance_events(db, session_id)


@router.get("/dashboard/sessions/{session_id}/attendance", response_class=HTMLResponse)
def dashboard_attendance(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ensure_attendance_records_for_session(db, session)
    return templates.TemplateResponse(
        request,
        "attendance/detail.html",
        {
            "session": session,
            "records": get_attendance_records(db, session_id),
            "events": get_attendance_events(db, session_id),
            "statuses": list(AttendanceStatus),
            "scan_result": request.query_params.get("scan_result"),
            "scan_message": request.query_params.get("scan_message"),
        },
    )


@router.post("/dashboard/attendance/scan-qr")
def dashboard_scan_qr_attendance(
    session_id: int = Form(...),
    qr_code: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        result = scan_qr_attendance(
            db=db,
            qr_code=qr_code,
            session_id=session_id,
            raw_source="dashboard_manual_qr_input",
        )
        message = result["message"].replace(" ", "+")
        return RedirectResponse(
            url=f"/dashboard/sessions/{session_id}/attendance?scan_result={result['result']}&scan_message={message}",
            status_code=303,
        )
    except ValueError as exc:
        message = str(exc).replace(" ", "+")
        return RedirectResponse(
            url=f"/dashboard/sessions/{session_id}/attendance?scan_result=error&scan_message={message}",
            status_code=303,
        )


@router.post("/dashboard/attendance/{record_id}/override")
def dashboard_override_attendance(
    record_id: int,
    status: str = Form(...),
    override_reason: str = Form(...),
    db: Session = Depends(get_db),
):
    record = get_attendance_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    override_attendance_record(
        db=db,
        record=record,
        status=AttendanceStatus(status),
        overridden_by=1,
        reason=override_reason,
    )
    return RedirectResponse(url=f"/dashboard/sessions/{record.session_id}/attendance", status_code=303)



# Phase 4 face attendance routes
from app.schemas.face_schema import FaceRecognitionRequest
from app.services.face_service import simulate_face_attendance


@router.post("/api/attendance/face-recognize")
def api_face_recognize(data: FaceRecognitionRequest, db: Session = Depends(get_db)):
    try:
        return simulate_face_attendance(
            db=db,
            student_id=data.student_id,
            session_id=data.session_id,
            confidence=data.confidence,
            raw_source=data.raw_source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/dashboard/attendance/face-simulate")
def dashboard_face_simulate(
    session_id: int = Form(...),
    student_id: int = Form(...),
    confidence: float = Form(0.86),
    db: Session = Depends(get_db),
):
    try:
        result = simulate_face_attendance(
            db=db,
            student_id=student_id,
            session_id=session_id,
            confidence=confidence,
            raw_source="dashboard_face_simulation",
        )
        message = result["message"].replace(" ", "+")
        return RedirectResponse(
            url=f"/dashboard/sessions/{session_id}/attendance?scan_result={result['result']}&scan_message={message}",
            status_code=303,
        )
    except ValueError as exc:
        message = str(exc).replace(" ", "+")
        return RedirectResponse(
            url=f"/dashboard/sessions/{session_id}/attendance?scan_result=error&scan_message={message}",
            status_code=303,
        )
