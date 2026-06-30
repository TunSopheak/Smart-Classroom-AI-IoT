from app.models.academic import ClassGroup, StudentEnrollment
from app.models.student import Student
from fastapi import Form, Depends
from urllib.parse import quote_plus
from app.services.academic_rules import validate_weekly_schedule_rule

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.academic import ClassGroup, Course, StudentEnrollment, WeeklySchedule
from app.models.class_session import ClassSession


router = APIRouter(tags=["Academic Lifecycle"])


def redirect_class_setup(message: str = ""):
    url = "/dashboard/class-setup"
    if message:
        url += f"?message={message}"
    return RedirectResponse(url=url, status_code=303)


def redirect_sessions(message: str = ""):
    url = "/dashboard/sessions"
    if message:
        url += f"?message={message}"
    return RedirectResponse(url=url, status_code=303)


@router.post("/dashboard/class-setup/class-groups/{group_id}/update")
def update_class_group(
    group_id: int,
    code: str = Form(...),
    name: str = Form(...),
    academic_year: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    group = db.query(ClassGroup).filter(ClassGroup.id == group_id).first()

    if not group:
        return redirect_class_setup("Class group not found")

    normalized_code = code.strip().upper()

    duplicate = (
        db.query(ClassGroup)
        .filter(ClassGroup.code == normalized_code)
        .filter(ClassGroup.id != group_id)
        .first()
    )

    if duplicate:
        return redirect_class_setup("Class group code already exists")

    group.code = normalized_code
    group.name = name.strip()
    group.academic_year = academic_year.strip() or None
    group.description = description.strip() or None
    group.active = True

    db.commit()
    return redirect_class_setup("Class group updated")


@router.post("/dashboard/class-setup/class-groups/{group_id}/deactivate")
def deactivate_class_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(ClassGroup).filter(ClassGroup.id == group_id).first()

    if not group:
        return redirect_class_setup("Class group not found")

    active_session = (
        db.query(ClassSession)
        .filter(ClassSession.class_group_id == group.id)
        .filter(ClassSession.active == True)
        .first()
    )

    if active_session:
        return redirect_class_setup("Cannot deactivate class group while it has an active session")

    group.active = False
    db.commit()
    return redirect_class_setup("Class group deactivated")


@router.post("/dashboard/class-setup/courses/{course_id}/update")
def update_course(
    course_id: int,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        return redirect_class_setup("Course not found")

    normalized_code = code.strip().upper()

    duplicate = (
        db.query(Course)
        .filter(Course.code == normalized_code)
        .filter(Course.id != course_id)
        .first()
    )

    if duplicate:
        return redirect_class_setup("Course code already exists")

    course.code = normalized_code
    course.name = name.strip()
    course.description = description.strip() or None
    course.active = True

    db.commit()
    return redirect_class_setup("Course updated")


@router.post("/dashboard/class-setup/courses/{course_id}/deactivate")
def deactivate_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        return redirect_class_setup("Course not found")

    active_session = (
        db.query(ClassSession)
        .filter(ClassSession.course_id == course.id)
        .filter(ClassSession.active == True)
        .first()
    )

    if active_session:
        return redirect_class_setup("Cannot deactivate course while it has an active session")

    course.active = False
    db.commit()
    return redirect_class_setup("Course deactivated")


@router.post("/dashboard/class-setup/schedules/{schedule_id}/update")
def update_weekly_schedule(
    schedule_id: int,
    class_group_id: int = Form(...),
    course_id: int = Form(...),
    weekday: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    late_after_minutes: int = Form(15),
    location: str = Form(""),
    db: Session = Depends(get_db),
):
    schedule = db.query(WeeklySchedule).filter(WeeklySchedule.id == schedule_id).first()

    if not schedule:
        return redirect_class_setup("Schedule not found")

    ok, message, normalized_start, normalized_end = validate_weekly_schedule_rule(
        db=db,
        class_group_id=class_group_id,
        course_id=course_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        exclude_schedule_id=schedule_id,
    )

    if not ok:
        return redirect_class_setup(message)

    start_time = normalized_start
    end_time = normalized_end


    duplicate = (
        db.query(WeeklySchedule)
        .filter(WeeklySchedule.id != schedule_id)
        .filter(WeeklySchedule.class_group_id == class_group_id)
        .filter(WeeklySchedule.course_id == course_id)
        .filter(WeeklySchedule.weekday == weekday)
        .filter(WeeklySchedule.start_time == start_time)
        .filter(WeeklySchedule.end_time == end_time)
        .first()
    )

    if duplicate:
        return redirect_class_setup("A similar weekly schedule already exists")

    schedule.class_group_id = class_group_id
    schedule.course_id = course_id
    schedule.weekday = weekday
    schedule.start_time = start_time
    schedule.end_time = end_time
    schedule.late_after_minutes = late_after_minutes
    schedule.location = location.strip() or None
    schedule.active = True

    db.commit()
    return redirect_class_setup("Weekly schedule updated. Existing sessions keep their original history")


@router.post("/dashboard/class-setup/schedules/{schedule_id}/deactivate")
def deactivate_weekly_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(WeeklySchedule).filter(WeeklySchedule.id == schedule_id).first()

    if not schedule:
        return redirect_class_setup("Schedule not found")

    schedule.active = False
    db.commit()
    return redirect_class_setup("Weekly schedule deactivated. Existing sessions are not changed")


@router.post("/dashboard/class-setup/enrollments/{enrollment_id}/deactivate")
def deactivate_enrollment(enrollment_id: int, db: Session = Depends(get_db)):
    enrollment = db.query(StudentEnrollment).filter(StudentEnrollment.id == enrollment_id).first()

    if not enrollment:
        return redirect_class_setup("Enrollment not found")

    enrollment.active = False
    db.commit()
    return redirect_class_setup("Student removed from class group")


@router.post("/dashboard/sessions/{session_id}/archive")
def archive_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ClassSession).filter(ClassSession.id == session_id).first()

    if not session:
        return redirect_sessions("Session not found")

    if session.active:
        return redirect_sessions("Close the session before archiving it")

    session.archived = True
    db.commit()

    return redirect_sessions("Session archived")



# Phase 16.2.4 schedule manager helpers
def redirect_class_setup_v2(message: str = "", selected_group_id: int | None = None):
    url = "/dashboard/class-setup"

    params = []

    if selected_group_id:
        params.append(f"selected_group_id={selected_group_id}")

    if message:
        params.append(f"message={quote_plus(message)}")

    if params:
        url += "?" + "&".join(params)

    return RedirectResponse(url=url, status_code=303)


@router.post("/dashboard/class-setup/schedules/manage-create")
def create_weekly_schedule_from_manager(
    class_group_id: int = Form(...),
    course_id: int = Form(...),
    weekday: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    late_after_minutes: int = Form(15),
    location: str = Form(""),
    db: Session = Depends(get_db),
):
    ok, message, normalized_start, normalized_end = validate_weekly_schedule_rule(
        db=db,
        class_group_id=class_group_id,
        course_id=course_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
    )

    if not ok:
        return redirect_class_setup_v2(message, selected_group_id=class_group_id)

    schedule = WeeklySchedule(
        class_group_id=class_group_id,
        course_id=course_id,
        weekday=weekday,
        start_time=normalized_start,
        end_time=normalized_end,
        late_after_minutes=late_after_minutes,
        location=(location or "").strip() or None,
        active=True,
    )

    db.add(schedule)
    db.commit()

    return redirect_class_setup_v2("Weekly schedule created", selected_group_id=class_group_id)


@router.post("/dashboard/class-setup/schedules/{schedule_id}/reactivate")
def reactivate_weekly_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(WeeklySchedule).filter(WeeklySchedule.id == schedule_id).first()

    if not schedule:
        return redirect_class_setup_v2("Schedule not found")

    ok, message, normalized_start, normalized_end = validate_weekly_schedule_rule(
        db=db,
        class_group_id=schedule.class_group_id,
        course_id=schedule.course_id,
        weekday=schedule.weekday,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        exclude_schedule_id=schedule.id,
    )

    if not ok:
        return redirect_class_setup_v2(message, selected_group_id=schedule.class_group_id)

    schedule.start_time = normalized_start
    schedule.end_time = normalized_end
    schedule.active = True

    db.commit()

    return redirect_class_setup_v2("Weekly schedule reactivated", selected_group_id=schedule.class_group_id)


@router.post("/dashboard/class-setup/schedules/{schedule_id}/safe-delete")
def safe_delete_weekly_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(WeeklySchedule).filter(WeeklySchedule.id == schedule_id).first()

    if not schedule:
        return redirect_class_setup_v2("Schedule not found")

    selected_group_id = schedule.class_group_id

    generated_sessions = (
        db.query(ClassSession)
        .filter(ClassSession.weekly_schedule_id == schedule.id)
        .count()
    )

    if generated_sessions > 0:
        schedule.active = False
        db.commit()
        return redirect_class_setup_v2(
            f"Schedule has {generated_sessions} session history, so it was deactivated instead of deleted",
            selected_group_id=selected_group_id,
        )

    db.delete(schedule)
    db.commit()

    return redirect_class_setup_v2("Unused schedule deleted", selected_group_id=selected_group_id)



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
