from pathlib import Path

print("Applying Phase 3: Student Management + QR Code Images...")

Path("app/services/qr_service.py").write_text(r'''from pathlib import Path
import re

import qrcode


def safe_filename(value: str) -> str:
    """Convert student ID / QR value into a safe image filename."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return cleaned or "qr_code"


def build_student_qr_code(stu_id: str) -> str:
    """Standard QR value format for Smart Classroom students."""
    return f"SC-STUDENT-{stu_id.strip().upper()}"


def generate_qr_image(qr_value: str, output_dir: Path, filename: str) -> str:
    """Generate one QR image and return filesystem path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / filename

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_value)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(file_path)

    return str(file_path)


def generate_student_qr_image(stu_id: str, qr_code: str) -> str:
    """Generate QR image for one student and return browser static path."""
    output_dir = Path("app/static/generated_qr")
    filename = f"{safe_filename(stu_id)}.png"
    file_path = generate_qr_image(qr_code, output_dir, filename)
    return file_path.replace("app/static/", "/static/").replace("\\", "/")
''', encoding="utf-8")


Path("app/schemas/student_schema.py").write_text(r'''from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class StudentBase(BaseModel):
    stu_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=120)
    gender: str | None = None
    qr_code: str | None = None
    qr_image_path: str | None = None
    face_dataset_path: str | None = None
    active: bool = True


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    stu_id: str | None = None
    name: str | None = None
    gender: str | None = None
    qr_code: str | None = None
    qr_image_path: str | None = None
    face_dataset_path: str | None = None
    active: bool | None = None


class StudentRead(StudentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
''', encoding="utf-8")


Path("app/crud/student_crud.py").write_text(r'''from sqlalchemy.orm import Session

from app.models.student import Student
from app.schemas.student_schema import StudentCreate, StudentUpdate


def get_students(db: Session, skip: int = 0, limit: int = 200):
    return db.query(Student).order_by(Student.id).offset(skip).limit(limit).all()


def get_active_students(db: Session):
    return db.query(Student).filter(Student.active.is_(True)).order_by(Student.id).all()


def get_student(db: Session, student_id: int):
    return db.query(Student).filter(Student.id == student_id).first()


def get_student_by_stu_id(db: Session, stu_id: str):
    return db.query(Student).filter(Student.stu_id == stu_id).first()


def get_student_by_qr_code(db: Session, qr_code: str):
    return db.query(Student).filter(Student.qr_code == qr_code).first()


def create_student(db: Session, data: StudentCreate):
    student = Student(**data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def update_student(db: Session, student: Student, data: StudentUpdate):
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(student, key, value)
    db.commit()
    db.refresh(student)
    return student


def deactivate_student(db: Session, student: Student):
    student.active = False
    db.commit()
    db.refresh(student)
    return student


def activate_student(db: Session, student: Student):
    student.active = True
    db.commit()
    db.refresh(student)
    return student
''', encoding="utf-8")


Path("app/routers/student_router.py").write_text(r'''from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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
from app.schemas.student_schema import StudentCreate, StudentRead, StudentUpdate
from app.services.qr_service import build_student_qr_code, generate_student_qr_image

router = APIRouter(tags=["Students"])
templates = Jinja2Templates(directory="app/templates")


def ensure_student_qr(db: Session, student):
    """Make sure a student has QR value and QR image path."""
    if not student.qr_code:
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


@router.get("/api/students", response_model=list[StudentRead])
def api_list_students(db: Session = Depends(get_db)):
    return get_students(db)


@router.post("/api/students", response_model=StudentRead)
def api_create_student(data: StudentCreate, db: Session = Depends(get_db)):
    try:
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
    return templates.TemplateResponse(
        request,
        "students/list.html",
        {
            "students": get_students(db),
            "message": request.query_params.get("message"),
        },
    )


@router.post("/dashboard/students/create")
def dashboard_create_student(
    stu_id: str = Form(...),
    name: str = Form(...),
    gender: str = Form(""),
    db: Session = Depends(get_db),
):
    clean_stu_id = stu_id.strip().upper()
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
''', encoding="utf-8")


Path("app/templates/students/list.html").write_text(r'''{% extends "base.html" %}
{% block content %}
<section class="page-header">
    <div>
        <p class="eyebrow">Phase 3 Student Management</p>
        <h1>Students</h1>
        <p class="muted">Manage student identity, QR images, and active status. Attendance status is still stored per session only.</p>
    </div>
    <form action="/dashboard/students/generate-all-qr" method="post">
        <button class="secondary-button" type="submit">Generate All QR</button>
    </form>
</section>

{% if message %}
<section class="alert">
    {{ message }}
</section>
{% endif %}

<form class="form-card" action="/dashboard/students/create" method="post">
    <h2>Add Student</h2>
    <div class="form-row">
        <input name="stu_id" placeholder="Student ID, e.g. S006" required>
        <input name="name" placeholder="Student Name" required>
        <input name="gender" placeholder="Gender">
        <button type="submit">Add Student</button>
    </div>
    <p class="muted">New students are automatically given QR value, QR image, face dataset path, and demo classroom enrollment.</p>
</form>

<section class="panel">
    <h2>Student List</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>QR</th>
                <th>Student</th>
                <th>QR Value</th>
                <th>Face Dataset</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
        {% for student in students %}
            <tr class="{% if not student.active %}inactive-row{% endif %}">
                <td>{{ student.id }}</td>
                <td>
                    {% if student.qr_image_path %}
                        <img class="qr-thumb" src="{{ student.qr_image_path }}" alt="QR {{ student.stu_id }}">
                    {% else %}
                        <span class="muted">No QR</span>
                    {% endif %}
                </td>
                <td>
                    <strong>{{ student.stu_id }} - {{ student.name }}</strong><br>
                    <span class="small-text">Gender: {{ student.gender or '-' }}</span>
                </td>
                <td><code>{{ student.qr_code or '-' }}</code></td>
                <td class="small-text">{{ student.face_dataset_path or '-' }}</td>
                <td>
                    {% if student.active %}
                        <span class="badge-soft active-badge">Active</span>
                    {% else %}
                        <span class="badge-soft closed-badge">Inactive</span>
                    {% endif %}
                </td>
                <td>
                    <div class="table-actions">
                        <a class="button small-button" href="/dashboard/students/{{ student.id }}">Detail</a>
                        <form action="/dashboard/students/{{ student.id }}/generate-qr" method="post">
                            <button class="secondary-button small-button" type="submit">QR</button>
                        </form>
                        <a class="secondary-button small-button" href="/dashboard/students/{{ student.id }}/print-qr">Print</a>

                        {% if student.active %}
                            <form action="/dashboard/students/{{ student.id }}/deactivate" method="post">
                                <button class="danger-button small-button" type="submit">Deactivate</button>
                            </form>
                        {% else %}
                            <form action="/dashboard/students/{{ student.id }}/activate" method="post">
                                <button class="secondary-button small-button" type="submit">Activate</button>
                            </form>
                        {% endif %}
                    </div>
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</section>
{% endblock %}
''', encoding="utf-8")


Path("app/templates/students/detail.html").write_text(r'''{% extends "base.html" %}
{% block content %}
<section class="page-header">
    <div>
        <p class="eyebrow">Student Detail</p>
        <h1>{{ student.stu_id }} - {{ student.name }}</h1>
        <p class="muted">Permanent identity data. Do not store attendance status here.</p>
    </div>
    <div class="action-row">
        <a class="button secondary-button" href="/dashboard/students">Back Students</a>
        <a class="button" href="/dashboard/students/{{ student.id }}/print-qr">Print QR</a>
    </div>
</section>

{% if message %}
<section class="alert">{{ message }}</section>
{% endif %}

<section class="student-detail-grid">
    <div class="panel qr-card">
        <h2>Student QR Code</h2>
        {% if student.qr_image_path %}
            <img class="qr-large" src="{{ student.qr_image_path }}" alt="QR {{ student.stu_id }}">
        {% else %}
            <p class="muted">No QR image generated yet.</p>
        {% endif %}
        <p><strong>QR Value:</strong></p>
        <p><code>{{ student.qr_code or '-' }}</code></p>

        <form action="/dashboard/students/{{ student.id }}/generate-qr" method="post">
            <button type="submit">Generate / Refresh QR</button>
        </form>
    </div>

    <form class="panel" action="/dashboard/students/{{ student.id }}/update" method="post">
        <h2>Edit Student</h2>

        <label>Student ID</label>
        <input name="stu_id" value="{{ student.stu_id }}" required>

        <label>Name</label>
        <input name="name" value="{{ student.name }}" required>

        <label>Gender</label>
        <input name="gender" value="{{ student.gender or '' }}">

        <label>QR Code Value</label>
        <input name="qr_code" value="{{ student.qr_code or '' }}">

        <label>Face Dataset Path</label>
        <input name="face_dataset_path" value="{{ student.face_dataset_path or '' }}">

        <button type="submit">Save Changes</button>
    </form>
</section>

<section class="panel">
    <h2>Student System Info</h2>
    <div class="info-grid">
        <div><span>Status</span><strong>{{ 'Active' if student.active else 'Inactive' }}</strong></div>
        <div><span>Created</span><strong>{{ student.created_at }}</strong></div>
        <div><span>Updated</span><strong>{{ student.updated_at }}</strong></div>
        <div><span>Face Dataset</span><strong>{{ student.face_dataset_path or '-' }}</strong></div>
    </div>

    <div class="action-row">
        {% if student.active %}
            <form action="/dashboard/students/{{ student.id }}/deactivate" method="post">
                <button class="danger-button" type="submit">Deactivate Student</button>
            </form>
        {% else %}
            <form action="/dashboard/students/{{ student.id }}/activate" method="post">
                <button class="secondary-button" type="submit">Activate Student</button>
            </form>
        {% endif %}
    </div>
</section>
{% endblock %}
''', encoding="utf-8")


Path("app/templates/students/print_qr.html").write_text(r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Print QR - {{ student.stu_id }}</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body class="print-body">
    <main class="print-card">
        <h1>Smart Classroom Attendance QR</h1>

        {% if student.qr_image_path %}
            <img class="print-qr" src="{{ student.qr_image_path }}" alt="QR {{ student.stu_id }}">
        {% else %}
            <p>No QR image available.</p>
        {% endif %}

        <h2>{{ student.stu_id }}</h2>
        <h3>{{ student.name }}</h3>
        <p><code>{{ student.qr_code }}</code></p>

        <div class="no-print action-row print-actions">
            <button onclick="window.print()">Print</button>
            <a class="button secondary-button" href="/dashboard/students/{{ student.id }}">Back</a>
        </div>
    </main>
</body>
</html>
''', encoding="utf-8")


css_path = Path("app/static/css/styles.css")
css = css_path.read_text(encoding="utf-8")

phase3_css = r'''

/* Phase 3 Student management + QR images */
.qr-thumb {
    width: 58px;
    height: 58px;
    object-fit: contain;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: #ffffff;
    padding: 4px;
}

.qr-large {
    width: 260px;
    max-width: 100%;
    object-fit: contain;
    border: 1px solid var(--line);
    border-radius: 18px;
    background: #ffffff;
    padding: 12px;
    margin-bottom: 14px;
}

.qr-card {
    text-align: center;
}

.student-detail-grid {
    display: grid;
    grid-template-columns: 360px 1fr;
    gap: 18px;
    margin-bottom: 18px;
}

.info-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(160px, 1fr));
    gap: 12px;
}

.info-grid div {
    background: #f8fafc;
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 12px;
}

.info-grid span {
    display: block;
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 6px;
}

.info-grid strong {
    font-size: 14px;
    word-break: break-word;
}

.inactive-row {
    opacity: 0.65;
    background: #f8fafc;
}

.print-body {
    background: #ffffff;
    margin: 0;
    padding: 30px;
}

.print-card {
    max-width: 420px;
    margin: 0 auto;
    text-align: center;
    border: 2px solid #0f172a;
    border-radius: 24px;
    padding: 28px;
}

.print-card h1 {
    font-size: 22px;
    margin-bottom: 18px;
}

.print-card h2 {
    font-size: 34px;
    margin: 12px 0 4px;
}

.print-card h3 {
    font-size: 24px;
    margin: 0 0 12px;
}

.print-qr {
    width: 280px;
    max-width: 100%;
    object-fit: contain;
}

.print-actions {
    justify-content: center;
    margin-top: 20px;
}

label {
    display: block;
    margin: 12px 0 6px;
    color: var(--muted);
    font-weight: 700;
    font-size: 13px;
}

@media (max-width: 900px) {
    .student-detail-grid,
    .info-grid {
        grid-template-columns: 1fr;
    }
}

@media print {
    .no-print {
        display: none !important;
    }

    .print-body {
        padding: 0;
    }

    .print-card {
        border: none;
        margin-top: 20px;
    }
}
'''

if "/* Phase 3 Student management + QR images */" not in css:
    css_path.write_text(css + phase3_css, encoding="utf-8")


Path("generate_existing_qr.py").write_text(r'''from app.database.database import SessionLocal
from app.crud.student_crud import get_students
from app.services.qr_service import build_student_qr_code, generate_student_qr_image

db = SessionLocal()
try:
    students = get_students(db)
    for student in students:
        if not student.qr_code:
            student.qr_code = build_student_qr_code(student.stu_id)
        student.qr_image_path = generate_student_qr_image(student.stu_id, student.qr_code)
        print(f"Generated QR for {student.stu_id}: {student.qr_image_path}")
    db.commit()
    print(f"Done. Generated/refreshed QR images for {len(students)} students.")
finally:
    db.close()
''', encoding="utf-8")

print("DONE: Phase 3 files updated.")
print("Changed files:")
print("- app/services/qr_service.py")
print("- app/schemas/student_schema.py")
print("- app/crud/student_crud.py")
print("- app/routers/student_router.py")
print("- app/templates/students/list.html")
print("- app/templates/students/detail.html")
print("- app/templates/students/print_qr.html")
print("- app/static/css/styles.css")
print("- generate_existing_qr.py")
