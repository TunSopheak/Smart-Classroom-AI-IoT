from app.services.academic_rules import validate_weekly_schedule_rule, class_has_active_session
from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.academic_service import generate_class_group_code, generate_course_code
from app.database.database import get_db
from app.models.academic import ClassGroup, Course, StudentEnrollment, WeeklySchedule
from app.models.student import Student
from app.services.academic_service import WEEKDAY_LABELS, create_session_from_schedule

router = APIRouter(tags=["Class Setup"])
templates = Jinja2Templates(directory="app/templates")


def class_setup_redirect(message: str = "") -> RedirectResponse:
    suffix = f"?message={message}" if message else ""
    return RedirectResponse(url=f"/dashboard/class-setup{suffix}", status_code=303)


@router.get("/dashboard/class-setup", response_class=HTMLResponse)
def class_setup_page(request: Request, selected_group_id: int | None = None, db: Session = Depends(get_db)):
    class_groups = db.query(ClassGroup).order_by(ClassGroup.code).all()
    courses = db.query(Course).order_by(Course.code).all()
    schedules = db.query(WeeklySchedule).order_by(WeeklySchedule.weekday, WeeklySchedule.start_time).all()

    selected_group = None
    if selected_group_id:
        selected_group = db.query(ClassGroup).filter(ClassGroup.id == selected_group_id).first()
    if not selected_group and class_groups:
        selected_group = class_groups[0]

    enrolled_students = []
    unenrolled_students = []
    if selected_group:
        active_enrollments = (
            db.query(StudentEnrollment)
            .filter(
                StudentEnrollment.class_group_id == selected_group.id,
                StudentEnrollment.active.is_(True),
            )
            .all()
        )
        enrolled_ids = {item.student_id for item in active_enrollments}
        enrolled_students = [item.student for item in active_enrollments if item.student]
        unenrolled_students = (
            db.query(Student)
            .filter(Student.active.is_(True), ~Student.id.in_(enrolled_ids or {0}))
            .order_by(Student.stu_id)
            .all()
        )

    today_weekday = date.today().weekday()
    todays_schedules = [item for item in schedules if item.active and item.weekday == today_weekday]

    return templates.TemplateResponse(
        request,
        "class_setup/index.html",
        {
            "request": request,
            "class_groups": class_groups,
            "all_students": db.query(Student).order_by(Student.id).all(),
            "courses": courses,
            "schedules": schedules,
            "selected_group": selected_group,
            "enrolled_students": enrolled_students,
            "unenrolled_students": unenrolled_students,
            "weekday_labels": WEEKDAY_LABELS,
            "todays_schedules": todays_schedules,
            "message": request.query_params.get("message"),
        },
    )


@router.post("/dashboard/class-setup/class-groups")
def create_class_group(
    code: str = Form(''),
    name: str = Form(...),
    academic_year: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    class_group = ClassGroup(
        code=(code.strip() or generate_class_group_code(db)).upper(),
        name=name.strip(),
        academic_year=academic_year.strip() or None,
        description=description.strip() or None,
        active=True,
    )
    db.add(class_group)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return class_setup_redirect("Class+group+code+already+exists")
    return class_setup_redirect("Class+group+added")


@router.post("/dashboard/class-setup/courses")
def create_course(
    code: str = Form(""),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    course_name = (name or "").strip()

    if not course_name:
        return RedirectResponse(
            url="/dashboard/class-setup?message=Course name is required",
            status_code=303,
        )

    normalized_code = (code or "").strip().upper()

    if not normalized_code:
        normalized_code = generate_course_code(db, course_name)

    duplicate = db.query(Course).filter(Course.code == normalized_code).first()

    if duplicate:
        return RedirectResponse(
            url="/dashboard/class-setup?message=Course code already exists",
            status_code=303,
        )

    course = Course(
        code=normalized_code,
        name=course_name,
        description=(description or "").strip() or None,
        active=True,
    )

    db.add(course)
    db.commit()

    return RedirectResponse(
        url="/dashboard/class-setup?message=Course created",
        status_code=303,
    )

@router.post("/dashboard/class-setup/enroll")
def enroll_student(
    class_group_id: int = Form(...),
    student_id: int = Form(...),
    db: Session = Depends(get_db),
):
    enrollment = (
        db.query(StudentEnrollment)
        .filter(StudentEnrollment.class_group_id == class_group_id, StudentEnrollment.student_id == student_id)
        .first()
    )
    if enrollment:
        enrollment.active = True
    else:
        db.add(StudentEnrollment(class_group_id=class_group_id, student_id=student_id, active=True))
    db.commit()
    return RedirectResponse(url=f"/dashboard/class-setup?selected_group_id={class_group_id}&message=Student+enrolled", status_code=303)


@router.post("/dashboard/class-setup/enrollments/{enrollment_student_id}/deactivate")
def deactivate_enrollment(
    enrollment_student_id: int,
    class_group_id: int = Form(...),
    db: Session = Depends(get_db),
):
    enrollment = (
        db.query(StudentEnrollment)
        .filter(
            StudentEnrollment.class_group_id == class_group_id,
            StudentEnrollment.student_id == enrollment_student_id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    enrollment.active = False
    db.commit()
    return RedirectResponse(url=f"/dashboard/class-setup?selected_group_id={class_group_id}&message=Enrollment+removed", status_code=303)


@router.post("/dashboard/class-setup/schedules")
def create_weekly_schedule(
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
        return RedirectResponse(
            url=f"/dashboard/class-setup?message={message}",
            status_code=303,
        )

    start_time = normalized_start
    end_time = normalized_end

    schedule = WeeklySchedule(
        class_group_id=class_group_id,
        course_id=course_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        late_after_minutes=late_after_minutes,
        location=location.strip() or None,
        active=True,
    )
    db.add(schedule)
    db.commit()
    return class_setup_redirect("Weekly+schedule+added")


@router.post("/dashboard/class-setup/schedules/{schedule_id}/create-today")
def create_today_session(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(WeeklySchedule).filter(WeeklySchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Weekly schedule not found")
    session = create_session_from_schedule(db, schedule)
    return RedirectResponse(url=f"/dashboard/sessions/{session.id}/attendance", status_code=303)
