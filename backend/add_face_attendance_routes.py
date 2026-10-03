from pathlib import Path

student_router = Path("app/routers/student_router.py")
text = student_router.read_text(encoding="utf-8")

if "# Phase 4 face profile routes" not in text:
    text += r'''


# Phase 4 face profile routes
@router.get("/dashboard/students/{student_id}/face-profile", response_class=HTMLResponse)
def dashboard_student_face_profile(student_id: int, request: Request, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    from app.services.face_service import get_or_create_face_profile_summary

    profile = get_or_create_face_profile_summary(db, student)

    return templates.TemplateResponse(
        request,
        "students/face_profile.html",
        {
            "student": student,
            "profile": profile,
            "message": request.query_params.get("message"),
        },
    )


@router.post("/dashboard/students/{student_id}/face-profile/initialize")
def dashboard_initialize_student_face_profile(student_id: int, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    from app.services.face_service import get_or_create_face_profile_summary

    get_or_create_face_profile_summary(db, student)

    return RedirectResponse(
        url=f"/dashboard/students/{student.id}/face-profile?message=Face+profile+initialized",
        status_code=303,
    )
'''
    student_router.write_text(text, encoding="utf-8")


attendance_router = Path("app/routers/attendance_router.py")
text = attendance_router.read_text(encoding="utf-8")

if "# Phase 4 face attendance routes" not in text:
    text += r'''


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
'''
    attendance_router.write_text(text, encoding="utf-8")

print("Step 2 done: face routes added.")
