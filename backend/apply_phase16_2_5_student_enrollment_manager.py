from pathlib import Path
import re

ROOT = Path(".")
BACKEND = ROOT / "backend"

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, text):
    Path(path).write_text(text, encoding="utf-8")
    print(f"Updated: {path}")

# 1) Add backend routes for add student + enroll, and move class
life_path = BACKEND / "app/routers/academic_lifecycle_router.py"
life = read(life_path)

imports = [
    "from urllib.parse import quote_plus",
    "from fastapi import Form, Depends",
    "from fastapi.responses import RedirectResponse",
    "from sqlalchemy.orm import Session",
    "from app.database.database import get_db",
    "from app.models.student import Student",
    "from app.models.academic import ClassGroup, StudentEnrollment",
]

for imp in imports:
    if imp not in life:
        life = imp + "\n" + life

student_logic = r'''


# Phase 16.2.5 Student Enrollment Manager
def redirect_class_setup_student(message: str = "", selected_group_id: int | None = None):
    url = "/dashboard/class-setup"
    params = []

    if selected_group_id:
        params.append(f"selected_group_id={selected_group_id}")

    if message:
        params.append(f"message={quote_plus(message)}")

    if params:
        url += "?" + "&".join(params)

    return RedirectResponse(url=url, status_code=303)


def get_student_code_value(student) -> str:
    for attr in ("stu_id", "student_code", "code"):
        if hasattr(student, attr):
            value = getattr(student, attr, None)
            if value:
                return str(value)
    return f"ID-{getattr(student, 'id', '')}"


def generate_next_student_code(db: Session) -> str:
    max_number = 0

    for student in db.query(Student).all():
        code = get_student_code_value(student).upper()
        match = re.match(r"^S(\d+)$", code)
        if match:
            max_number = max(max_number, int(match.group(1)))

    return f"S{max_number + 1:03d}"


def student_code_exists(db: Session, code: str) -> bool:
    for attr in ("stu_id", "student_code", "code"):
        if hasattr(Student, attr):
            if db.query(Student).filter(getattr(Student, attr) == code).first():
                return True
    return False


def normalize_gender(value: str) -> str:
    raw = (value or "").strip()

    allowed = {
        "M": "M",
        "F": "F",
        "Male": "M",
        "Female": "F",
        "Other": "Other",
        "Not specified": "Not specified",
        "": "Not specified",
    }

    return allowed.get(raw, "Not specified")


def build_qr_value(student_code: str) -> str:
    try:
        from app.services import qr_service

        for fn_name in (
            "generate_signed_qr_value",
            "generate_student_qr_value",
            "generate_qr_value",
        ):
            fn = getattr(qr_service, fn_name, None)
            if fn:
                try:
                    return fn(student_code)
                except TypeError:
                    try:
                        return fn(stu_id=student_code)
                    except TypeError:
                        pass
    except Exception:
        pass

    return f"SC-STUDENT-{student_code}"


def set_if_exists(obj, attr: str, value):
    if hasattr(obj, attr):
        setattr(obj, attr, value)


def enroll_student_to_class(db: Session, student_id: int, class_group_id: int):
    active_enrollments = db.query(StudentEnrollment).filter(
        StudentEnrollment.student_id == student_id
    ).all()

    for enrollment in active_enrollments:
        if hasattr(enrollment, "active"):
            enrollment.active = False

    existing = (
        db.query(StudentEnrollment)
        .filter(StudentEnrollment.student_id == student_id)
        .filter(StudentEnrollment.class_group_id == class_group_id)
        .first()
    )

    if existing:
        if hasattr(existing, "active"):
            existing.active = True
        return existing

    enrollment = StudentEnrollment(
        student_id=student_id,
        class_group_id=class_group_id,
        active=True,
    )

    db.add(enrollment)
    return enrollment


@router.post("/dashboard/class-setup/students/create-and-enroll")
def create_student_and_enroll_to_class(
    name: str = Form(...),
    gender: str = Form("Not specified"),
    class_group_id: int = Form(...),
    student_code: str = Form(""),
    db: Session = Depends(get_db),
):
    student_name = (name or "").strip()
    selected_group = db.query(ClassGroup).filter(ClassGroup.id == class_group_id).first()

    if not selected_group:
        return redirect_class_setup_student("Class group not found")

    if not student_name:
        return redirect_class_setup_student("Student name is required", selected_group_id=class_group_id)

    code = (student_code or "").strip().upper()
    if not code:
        code = generate_next_student_code(db)

    if student_code_exists(db, code):
        return redirect_class_setup_student(
            f"Student code {code} already exists",
            selected_group_id=class_group_id,
        )

    qr_value = build_qr_value(code)

    student = Student()

    set_if_exists(student, "stu_id", code)
    set_if_exists(student, "student_code", code)
    set_if_exists(student, "code", code)
    set_if_exists(student, "name", student_name)
    set_if_exists(student, "gender", normalize_gender(gender))
    set_if_exists(student, "status", "active")
    set_if_exists(student, "active", True)
    set_if_exists(student, "qr_value", qr_value)
    set_if_exists(student, "face_dataset_path", f"ai_module/face_recognition/datasets/{code}")

    db.add(student)
    db.flush()

    enroll_student_to_class(db, student.id, class_group_id)

    db.commit()

    return redirect_class_setup_student(
        f"Student {code} created and enrolled",
        selected_group_id=class_group_id,
    )


@router.post("/dashboard/class-setup/enrollment/move-student")
def move_student_class(
    student_id: int = Form(...),
    target_class_group_id: int = Form(...),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    target_group = db.query(ClassGroup).filter(ClassGroup.id == target_class_group_id).first()

    if not student:
        return redirect_class_setup_student("Student not found")

    if not target_group:
        return redirect_class_setup_student("Target class group not found")

    enroll_student_to_class(db, student.id, target_group.id)
    db.commit()

    return redirect_class_setup_student(
        f"{get_student_code_value(student)} moved to {target_group.code}",
        selected_group_id=target_group.id,
    )
'''

if "Phase 16.2.5 Student Enrollment Manager" not in life:
    life += student_logic

write(life_path, life)

# 2) Ensure class setup page receives all_students
class_router_path = BACKEND / "app/routers/class_setup_router.py"
class_router = read(class_router_path)

if "from app.models.student import Student" not in class_router:
    class_router = "from app.models.student import Student\n" + class_router

if '"all_students"' not in class_router and "'all_students'" not in class_router:
    inserted = False
    anchors = [
        '"class_groups": class_groups,',
        "'class_groups': class_groups,",
        '"courses": courses,',
        "'courses': courses,",
    ]

    for anchor in anchors:
        if anchor in class_router:
            class_router = class_router.replace(
                anchor,
                anchor + '\n            "all_students": db.query(Student).order_by(Student.id).all(),',
                1,
            )
            inserted = True
            break

    if not inserted:
        print("WARNING: Could not auto-insert all_students into class_setup_router context.")

write(class_router_path, class_router)

# 3) Improve Class Setup template: Add Student & Move Class manager
tpl_path = BACKEND / "app/templates/class_setup/index.html"
tpl = read(tpl_path)

student_manager = r'''

<section class="card student-enrollment-manager-card">
    <div class="section-title-row">
        <div>
            <p class="eyebrow">Student Lifecycle</p>
            <h2>Add Student & Class Enrollment</h2>
            <p class="muted">
                Student identity stays permanent. Class enrollment can be changed when a student moves class.
            </p>
        </div>
    </div>

    <div class="student-lifecycle-grid">
        <div class="student-lifecycle-panel">
            <h3>Add Student to Class</h3>
            <form method="post" action="/dashboard/class-setup/students/create-and-enroll" class="student-lifecycle-form">
                <label>
                    <span>Student name</span>
                    <input name="name" placeholder="Student full name" required>
                </label>

                <label>
                    <span>Gender</span>
                    <select name="gender" required>
                        <option value="M">Male</option>
                        <option value="F">Female</option>
                        <option value="Other">Other</option>
                        <option value="Not specified">Not specified</option>
                    </select>
                </label>

                <label>
                    <span>Class group</span>
                    <select name="class_group_id" required>
                        {% for group in class_groups|default([]) %}
                        {% if group.active %}
                        <option value="{{ group.id }}" {% if selected_group and selected_group.id == group.id %}selected{% endif %}>
                            {{ group.code }} - {{ group.name }}
                        </option>
                        {% endif %}
                        {% endfor %}
                    </select>
                </label>

                <details class="advanced-inline">
                    <summary>Advanced: manual student code</summary>
                    <label>
                        <span>Student code override</span>
                        <input name="student_code" placeholder="Leave empty for auto, e.g. S007">
                    </label>
                </details>

                <button class="btn btn-primary" type="submit">Add & Enroll</button>
            </form>
        </div>

        <div class="student-lifecycle-panel">
            <h3>Move Student to Another Class</h3>
            <form method="post" action="/dashboard/class-setup/enrollment/move-student" class="student-lifecycle-form">
                <label>
                    <span>Student</span>
                    <select name="student_id" required>
                        {% for student in all_students|default([]) %}
                        {% if student.active is not defined or student.active %}
                        <option value="{{ student.id }}">
                            {{ student.stu_id if student.stu_id is defined else student.id }} - {{ student.name }}
                        </option>
                        {% endif %}
                        {% endfor %}
                    </select>
                </label>

                <label>
                    <span>Move to class</span>
                    <select name="target_class_group_id" required>
                        {% for group in class_groups|default([]) %}
                        {% if group.active %}
                        <option value="{{ group.id }}" {% if selected_group and selected_group.id == group.id %}selected{% endif %}>
                            {{ group.code }} - {{ group.name }}
                        </option>
                        {% endif %}
                        {% endfor %}
                    </select>
                </label>

                <div class="safe-note">
                    Moving class deactivates the old enrollment but keeps student attendance and history.
                </div>

                <button class="btn btn-secondary" type="submit">Move Class</button>
            </form>
        </div>
    </div>
</section>
'''

if "Add Student & Class Enrollment" not in tpl:
    idx = tpl.find("Student Enrollment")
    if idx != -1:
        section_start = tpl.rfind("<section", 0, idx)
        if section_start != -1:
            tpl = tpl[:section_start] + student_manager + "\n" + tpl[section_start:]
        else:
            tpl += student_manager
    elif "{% endblock %}" in tpl:
        tpl = tpl.replace("{% endblock %}", student_manager + "\n{% endblock %}", 1)
    else:
        tpl += student_manager

write(tpl_path, tpl)

# 4) Patch Students page gender input into combo box if it is still text input
students_tpl_path = BACKEND / "app/templates/students/list.html"
if students_tpl_path.exists():
    students_tpl = read(students_tpl_path)

    gender_select = '''<select name="gender" required>
        <option value="M">Male</option>
        <option value="F">Female</option>
        <option value="Other">Other</option>
        <option value="Not specified">Not specified</option>
    </select>'''

    if '<select name="gender"' not in students_tpl:
        students_tpl = re.sub(
            r'<input\b[^>]*name=["\\\']gender["\\\'][^>]*>',
            gender_select,
            students_tpl,
            count=1,
            flags=re.I,
        )

    write(students_tpl_path, students_tpl)

# 5) CSS polish
css_path = BACKEND / "app/static/css/styles.css"
css = read(css_path)

css_patch = r"""

/* Phase 16.2.5 Student Enrollment Manager */
.student-enrollment-manager-card {
    margin-top: 1rem;
}

.student-lifecycle-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-top: 1rem;
}

.student-lifecycle-panel {
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    background: #f8fafc;
    padding: 1rem;
}

.student-lifecycle-panel h3 {
    font-size: 1rem !important;
    margin-bottom: 0.75rem;
}

.student-lifecycle-form {
    display: grid;
    gap: 0.75rem;
}

.student-lifecycle-form label {
    display: grid;
    gap: 0.35rem;
}

.student-lifecycle-form label span {
    color: #64748b;
    font-size: 0.74rem;
    font-weight: 900;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.student-lifecycle-form input,
.student-lifecycle-form select {
    height: 42px;
    min-width: 0;
    font-size: 0.9rem !important;
}

.advanced-inline {
    padding: 0.7rem;
    border: 1px dashed #cbd5e1;
    border-radius: 14px;
    background: #ffffff;
}

.advanced-inline summary {
    cursor: pointer;
    color: #475569;
    font-size: 0.85rem;
    font-weight: 800;
}

.advanced-inline label {
    margin-top: 0.7rem;
}

.safe-note {
    border: 1px solid #bfdbfe;
    border-radius: 14px;
    background: #eff6ff;
    color: #1e3a8a;
    padding: 0.7rem;
    font-size: 0.84rem;
    line-height: 1.45;
}

@media (max-width: 900px) {
    .student-lifecycle-grid {
        grid-template-columns: 1fr;
    }
}
"""

if "Phase 16.2.5 Student Enrollment Manager" not in css:
    css += css_patch
    write(css_path, css)

print("")
print("DONE: Phase 16.2.5 Student Enrollment Manager applied.")
