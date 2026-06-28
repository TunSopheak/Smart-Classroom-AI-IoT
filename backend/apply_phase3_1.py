from pathlib import Path

print("Applying Phase 3.1: QR Demo Workflow Improvements...")

Path("app/routers/student_router.py").write_text(r'''import csv
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
''', encoding="utf-8")


Path("app/templates/students/list.html").write_text(r'''{% extends "base.html" %}
{% block content %}
<section class="page-header">
    <div>
        <p class="eyebrow">Phase 3.1 QR Demo Workflow</p>
        <h1>Students</h1>
        <p class="muted">Manage student identity, QR images, printable QR cards, search, and filters.</p>
    </div>
    <div class="action-row">
        <form action="/dashboard/students/generate-all-qr" method="post">
            <button class="secondary-button" type="submit">Generate All QR</button>
        </form>
        <a class="button" href="/dashboard/students/print-all-qr">Print All QR</a>
        <a class="button secondary-button" href="/dashboard/students/export-qr.csv">Export CSV</a>
    </div>
</section>

{% if message %}
<section class="alert">
    {{ message }}
</section>
{% endif %}

<section class="cards student-stats">
    <div class="card"><span>Total Students</span><strong>{{ stats.total }}</strong></div>
    <div class="card success"><span>Active</span><strong>{{ stats.active }}</strong></div>
    <div class="card danger"><span>Inactive</span><strong>{{ stats.inactive }}</strong></div>
    <div class="card info"><span>With QR Image</span><strong>{{ stats.with_qr }}</strong></div>
</section>

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
    <div class="panel-title-row">
        <h2>Student List</h2>
        <span class="muted">{{ students|length }} result(s)</span>
    </div>

    <form class="search-toolbar" method="get" action="/dashboard/students">
        <input name="q" value="{{ q }}" placeholder="Search by ID, name, QR, gender...">
        <select name="status">
            <option value="all" {% if status_filter == "all" %}selected{% endif %}>All Students</option>
            <option value="active" {% if status_filter == "active" %}selected{% endif %}>Active Only</option>
            <option value="inactive" {% if status_filter == "inactive" %}selected{% endif %}>Inactive Only</option>
        </select>
        <button type="submit">Search</button>
        <a class="button secondary-button" href="/dashboard/students">Reset</a>
    </form>

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
        {% else %}
            <tr>
                <td colspan="7">
                    <p class="muted">No students found. Try another search or reset the filter.</p>
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</section>
{% endblock %}
''', encoding="utf-8")


Path("app/templates/students/print_all_qr.html").write_text(r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Print All Student QR Cards</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body class="print-all-body">
    <div class="no-print print-toolbar">
        <h1>Print All Student QR Cards</h1>
        <div class="action-row">
            <button onclick="window.print()">Print All</button>
            <a class="button secondary-button" href="/dashboard/students">Back Students</a>
        </div>
    </div>

    <main class="qr-print-grid">
        {% for student in students %}
            <section class="qr-print-card {% if not student.active %}inactive-print-card{% endif %}">
                <h2>Smart Classroom Attendance QR</h2>

                {% if student.qr_image_path %}
                    <img class="print-qr-small" src="{{ student.qr_image_path }}" alt="QR {{ student.stu_id }}">
                {% else %}
                    <p>No QR image</p>
                {% endif %}

                <h3>{{ student.stu_id }}</h3>
                <h4>{{ student.name }}</h4>
                <p><code>{{ student.qr_code or '-' }}</code></p>
                <p class="small-text">{{ 'Active' if student.active else 'Inactive' }}</p>
            </section>
        {% endfor %}
    </main>
</body>
</html>
''', encoding="utf-8")


css_path = Path("app/static/css/styles.css")
css = css_path.read_text(encoding="utf-8")

phase31_css = r'''

/* Phase 3.1 QR demo workflow */
.student-stats {
    margin-bottom: 18px;
}

.search-toolbar {
    display: grid;
    grid-template-columns: minmax(260px, 1fr) 180px auto auto;
    gap: 10px;
    align-items: center;
    margin-bottom: 18px;
}

.print-toolbar {
    max-width: 1100px;
    margin: 20px auto;
    padding: 16px;
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: center;
}

.print-all-body {
    background: #ffffff;
    padding: 0;
    margin: 0;
}

.qr-print-grid {
    max-width: 1100px;
    margin: 0 auto;
    padding: 20px;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 18px;
}

.qr-print-card {
    border: 2px solid #0f172a;
    border-radius: 20px;
    padding: 18px;
    text-align: center;
    break-inside: avoid;
    page-break-inside: avoid;
    min-height: 360px;
}

.qr-print-card h2 {
    font-size: 18px;
    margin: 0 0 12px;
}

.qr-print-card h3 {
    font-size: 30px;
    margin: 10px 0 2px;
}

.qr-print-card h4 {
    font-size: 20px;
    margin: 0 0 8px;
}

.print-qr-small {
    width: 190px;
    height: 190px;
    object-fit: contain;
}

.inactive-print-card {
    opacity: 0.45;
}

@media (max-width: 900px) {
    .search-toolbar {
        grid-template-columns: 1fr;
    }

    .qr-print-grid {
        grid-template-columns: 1fr;
    }
}

@media print {
    .no-print {
        display: none !important;
    }

    .print-all-body {
        background: #ffffff;
    }

    .qr-print-grid {
        max-width: none;
        padding: 0;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
    }

    .qr-print-card {
        min-height: 330px;
        border: 1.5px solid #000000;
    }

    .print-qr-small {
        width: 170px;
        height: 170px;
    }
}
'''

if "/* Phase 3.1 QR demo workflow */" not in css:
    css_path.write_text(css + phase31_css, encoding="utf-8")

print("DONE: Phase 3.1 files updated.")
print("Changed files:")
print("- app/routers/student_router.py")
print("- app/templates/students/list.html")
print("- app/templates/students/print_all_qr.html")
print("- app/static/css/styles.css")
