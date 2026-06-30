import csv
import re
from io import StringIO

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.student_crud import (
    activate_student,
    create_student,
    deactivate_student,
    get_student,
    get_students,
    update_student,
)
from app.database.database import get_db
from app.models.classroom import Classroom
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.schemas.student_schema import StudentCreate, StudentRead, StudentUpdate
from app.services.qr_service import build_student_qr_code, generate_student_qr_image, parse_signed_student_qr

router = APIRouter(tags=["Students"])
templates = Jinja2Templates(directory="app/templates")
STUDENT_CODE_PATTERN = re.compile(r"^S(\d+)$", re.IGNORECASE)


def generate_next_student_code(db: Session) -> str:
    """Generate the next S001-style code while preserving existing manual IDs."""
    max_number = 0
    for (stu_id,) in db.query(Student.stu_id).all():
        match = STUDENT_CODE_PATTERN.match(stu_id or "")
        if match:
            max_number = max(max_number, int(match.group(1)))

    next_number = max_number + 1
    while True:
        candidate = f"S{next_number:03d}"
        existing = db.query(Student).filter(Student.stu_id == candidate).first()
        if not existing:
            return candidate
        next_number += 1


def normalize_or_generate_student_code(db: Session, stu_id: str | None) -> str:
    clean_stu_id = (stu_id or "").strip().upper()
    if clean_stu_id:
        return clean_stu_id
    return generate_next_student_code(db)


def ensure_student_qr(db: Session, student):
    """Make sure a student has QR value and QR image path."""
    if not student.qr_code or parse_signed_student_qr(student.qr_code) != student.stu_id:
        student.qr_code = build_student_qr_code(student.stu_id)

    student.qr_image_path = generate_student_qr_image(student.stu_id, student.qr_code)
    db.commit()
    db.refresh(student)
    return student


def enroll_student_to_first_classroom(db: Session, student_id: int) -> None:
    """MVP helper: enroll new students into the first classroom automatically."""
    classroom = db.query(Classroom).order_by(Classroom.id).first()
    if not classroom:
        return

    existing = (
        db.query(Enrollment)
        .filter(
            Enrollment.classroom_id == classroom.id,
            Enrollment.student_id == student_id,
        )
        .first()
    )

    if existing:
        existing.active = True
    else:
        db.add(Enrollment(classroom_id=classroom.id, student_id=student_id, active=True))

    db.commit()


def filter_students(students, search_text: str = "", status_filter: str = "all"):
    """Filter students for dashboard search and active/inactive view."""
    q = search_text.strip().lower()
    filtered = students

    if status_filter == "active":
        filtered = [student for student in filtered if student.active]
    elif status_filter == "inactive":
        filtered = [student for student in filtered if not student.active]

    if q:
        filtered = [
            student for student in filtered
            if q in student.stu_id.lower()
            or q in student.name.lower()
            or q in (student.qr_code or "").lower()
            or q in (student.gender or "").lower()
        ]

    return filtered


def build_student_stats(students):
    total = len(students)
    active = len([student for student in students if student.active])
    inactive = total - active
    with_qr = len([student for student in students if student.qr_image_path])
    return {
        "total": total,
        "active": active,
        "inactive": inactive,
        "with_qr": with_qr,
    }


@router.get("/api/students", response_model=list[StudentRead])
def api_list_students(db: Session = Depends(get_db)):
    return get_students(db)


@router.post("/api/students", response_model=StudentRead)
def api_create_student(data: StudentCreate, db: Session = Depends(get_db)):
    try:
        clean_stu_id = normalize_or_generate_student_code(db, data.stu_id)
        data.stu_id = clean_stu_id
        data.qr_code = data.qr_code or build_student_qr_code(clean_stu_id)
        data.face_dataset_path = data.face_dataset_path or f"ai_module/face_recognition/datasets/{clean_stu_id}"
        student = create_student(db, data)
        enroll_student_to_first_classroom(db, student.id)
        ensure_student_qr(db, student)
        return student
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Student ID or QR code already exists") from exc


@router.get("/api/students/{student_id}", response_model=StudentRead)
def api_get_student(student_id: int, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.put("/api/students/{student_id}", response_model=StudentRead)
def api_update_student(student_id: int, data: StudentUpdate, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    try:
        updated = update_student(db, student, data)
        return updated
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Student ID or QR code already exists") from exc


@router.delete("/api/students/{student_id}", response_model=StudentRead)
def api_deactivate_student(student_id: int, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return deactivate_student(db, student)


@router.post("/api/students/{student_id}/activate", response_model=StudentRead)
def api_activate_student(student_id: int, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return activate_student(db, student)


@router.post("/api/students/{student_id}/generate-qr", response_model=StudentRead)
def api_generate_student_qr(student_id: int, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return ensure_student_qr(db, student)


@router.post("/api/students/generate-all-qr")
def api_generate_all_student_qr(db: Session = Depends(get_db)):
    students = get_students(db)
    for student in students:
        ensure_student_qr(db, student)
    return {"ok": True, "generated": len(students)}


@router.get("/dashboard/students", response_class=HTMLResponse)
def dashboard_students(request: Request, db: Session = Depends(get_db)):
    all_students = get_students(db)

    search_text = request.query_params.get("q", "")
    status_filter = request.query_params.get("status", "all")

    students = filter_students(
        students=all_students,
        search_text=search_text,
        status_filter=status_filter,
    )

    return templates.TemplateResponse(
        request,
        "students/list.html",
        {
            "students": students,
            "stats": build_student_stats(all_students),
            "message": request.query_params.get("message"),
            "q": search_text,
            "status_filter": status_filter,
        },
    )


@router.post("/dashboard/students/create")
def dashboard_create_student(
    stu_id: str = Form(""),
    name: str = Form(...),
    gender: str = Form(""),
    db: Session = Depends(get_db),
):
    clean_stu_id = normalize_or_generate_student_code(db, stu_id)
    data = StudentCreate(
        stu_id=clean_stu_id,
        name=name.strip(),
        gender=gender.strip() or None,
        qr_code=build_student_qr_code(clean_stu_id),
        face_dataset_path=f"ai_module/face_recognition/datasets/{clean_stu_id}",
        active=True,
    )

    try:
        student = create_student(db, data)
        enroll_student_to_first_classroom(db, student.id)
        ensure_student_qr(db, student)
        return RedirectResponse(url=f"/dashboard/students/{student.id}", status_code=303)
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url="/dashboard/students?message=Student+ID+or+QR+already+exists", status_code=303)


@router.get("/dashboard/students/export-qr.csv")
def dashboard_export_student_qr_csv(db: Session = Depends(get_db)):
    students = get_students(db)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "stu_id", "name", "gender", "qr_code", "qr_image_path", "active"])

    for student in students:
        writer.writerow([
            student.id,
            student.stu_id,
            student.name,
            student.gender or "",
            student.qr_code or "",
            student.qr_image_path or "",
            "Active" if student.active else "Inactive",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=smart_classroom_student_qr_list.csv"},
    )


@router.get("/dashboard/students/print-all-qr", response_class=HTMLResponse)
def dashboard_print_all_student_qr(request: Request, db: Session = Depends(get_db)):
    students = get_students(db)
    for student in students:
        if not student.qr_image_path:
            ensure_student_qr(db, student)

    students = get_students(db)
    return templates.TemplateResponse(
        request,
        "students/print_all_qr.html",
        {"students": students},
    )


@router.get("/dashboard/students/{student_id}", response_class=HTMLResponse)
def dashboard_student_detail(student_id: int, request: Request, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return templates.TemplateResponse(
        request,
        "students/detail.html",
        {
            "student": student,
            "message": request.query_params.get("message"),
        },
    )


@router.post("/dashboard/students/{student_id}/update")
def dashboard_update_student(
    student_id: int,
    stu_id: str = Form(...),
    name: str = Form(...),
    gender: str = Form(""),
    qr_code: str = Form(""),
    face_dataset_path: str = Form(""),
    db: Session = Depends(get_db),
):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    clean_stu_id = stu_id.strip().upper()
    data = StudentUpdate(
        stu_id=clean_stu_id,
        name=name.strip(),
        gender=gender.strip() or None,
        qr_code=qr_code.strip() or build_student_qr_code(clean_stu_id),
        face_dataset_path=face_dataset_path.strip() or f"ai_module/face_recognition/datasets/{clean_stu_id}",
    )

    try:
        update_student(db, student, data)
        ensure_student_qr(db, student)
        return RedirectResponse(url=f"/dashboard/students/{student.id}?message=Student+updated", status_code=303)
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url=f"/dashboard/students/{student_id}?message=Student+ID+or+QR+already+exists", status_code=303)


@router.post("/dashboard/students/{student_id}/generate-qr")
def dashboard_generate_student_qr(student_id: int, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    ensure_student_qr(db, student)
    return RedirectResponse(url=f"/dashboard/students/{student.id}?message=QR+image+generated", status_code=303)


@router.post("/dashboard/students/generate-all-qr")
def dashboard_generate_all_student_qr(db: Session = Depends(get_db)):
    students = get_students(db)
    for student in students:
        ensure_student_qr(db, student)

    return RedirectResponse(url="/dashboard/students?message=QR+images+generated+for+all+students", status_code=303)


@router.post("/dashboard/students/{student_id}/deactivate")
def dashboard_deactivate_student(student_id: int, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    deactivate_student(db, student)
    return RedirectResponse(url="/dashboard/students?message=Student+deactivated", status_code=303)


@router.post("/dashboard/students/{student_id}/activate")
def dashboard_activate_student(student_id: int, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    activate_student(db, student)
    return RedirectResponse(url="/dashboard/students?message=Student+activated", status_code=303)


@router.get("/dashboard/students/{student_id}/print-qr", response_class=HTMLResponse)
def dashboard_print_student_qr(student_id: int, request: Request, db: Session = Depends(get_db)):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if not student.qr_image_path:
        ensure_student_qr(db, student)

    return templates.TemplateResponse(
        request,
        "students/print_qr.html",
        {"student": student},
    )



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
