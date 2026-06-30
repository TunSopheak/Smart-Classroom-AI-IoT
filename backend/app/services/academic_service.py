from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models.academic import ClassGroup, Course, StudentEnrollment, WeeklySchedule
from app.models.class_session import ClassSession
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.subject import Subject
from app.schemas.session_schema import ClassSessionCreate
from app.crud.session_crud import create_session
from app.services.session_service import prepare_session_attendance


WEEKDAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_or_create_demo_class_group(db: Session) -> ClassGroup:
    class_group = db.query(ClassGroup).filter(ClassGroup.code == "CS-M4-Y3-G27").first()
    if class_group:
        return class_group

    class_group = ClassGroup(
        code="CS-M4-Y3-G27",
        name="Computer Science M4 Year 3 Generation 27",
        academic_year="2025-2026",
        description="Default demo class group for Smart Classroom academic workflow.",
        active=True,
    )
    db.add(class_group)
    db.commit()
    db.refresh(class_group)
    return class_group


def get_or_create_demo_course(db: Session) -> Course:
    course = db.query(Course).filter(Course.code == "IOT301").first()
    if course:
        return course

    course = Course(
        code="IOT301",
        name="IoT Project",
        description="Default demo course for the Smart Classroom project.",
        active=True,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def get_or_create_legacy_classroom(db: Session, class_group: ClassGroup) -> Classroom:
    classroom = db.query(Classroom).filter(Classroom.code == class_group.code).first()
    if classroom:
        return classroom

    classroom = Classroom(
        code=class_group.code,
        name=class_group.name,
        section="Group 1",
        shift="Demo",
        room="Smart Classroom Lab",
        active=True,
    )
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    return classroom


def get_or_create_legacy_subject(db: Session, course: Course) -> Subject:
    subject = db.query(Subject).filter(Subject.code == course.code).first()
    if subject:
        return subject

    subject = Subject(code=course.code, name=course.name, active=True)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


def get_or_create_demo_weekly_schedule(db: Session, class_group: ClassGroup, course: Course) -> WeeklySchedule:
    demo_weekday = date.today().weekday()
    schedule = (
        db.query(WeeklySchedule)
        .filter(
            WeeklySchedule.class_group_id == class_group.id,
            WeeklySchedule.course_id == course.id,
            WeeklySchedule.weekday == demo_weekday,
            WeeklySchedule.start_time == "06:00",
        )
        .first()
    )
    if schedule:
        return schedule

    schedule = WeeklySchedule(
        class_group_id=class_group.id,
        course_id=course.id,
        weekday=demo_weekday,
        start_time="06:00",
        end_time="08:00",
        late_after_minutes=15,
        location="Smart Classroom Lab",
        active=True,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def enroll_active_students_into_group(db: Session, class_group: ClassGroup) -> None:
    students = db.query(Student).filter(Student.active.is_(True)).all()
    changed = False
    for student in students:
        enrollment = (
            db.query(StudentEnrollment)
            .filter(
                StudentEnrollment.student_id == student.id,
                StudentEnrollment.class_group_id == class_group.id,
            )
            .first()
        )
        if enrollment:
            if not enrollment.active:
                enrollment.active = True
                changed = True
            continue

        db.add(StudentEnrollment(student_id=student.id, class_group_id=class_group.id, active=True))
        changed = True

    if changed:
        db.commit()


def seed_academic_demo_data(db: Session) -> dict:
    class_group = get_or_create_demo_class_group(db)
    course = get_or_create_demo_course(db)
    schedule = get_or_create_demo_weekly_schedule(db, class_group, course)
    get_or_create_legacy_classroom(db, class_group)
    get_or_create_legacy_subject(db, course)
    enroll_active_students_into_group(db, class_group)
    return {"class_group": class_group, "course": course, "schedule": schedule}


def parse_schedule_time(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def build_schedule_datetimes(schedule: WeeklySchedule, target_date: date) -> tuple[datetime, datetime, datetime]:
    start_clock = parse_schedule_time(schedule.start_time)
    end_clock = parse_schedule_time(schedule.end_time)
    start_at = datetime.combine(target_date, start_clock).replace(microsecond=0)
    close_at = datetime.combine(target_date, end_clock).replace(microsecond=0)
    if close_at <= start_at:
        close_at += timedelta(days=1)
    late_at = start_at + timedelta(minutes=schedule.late_after_minutes)
    return start_at, late_at, close_at


def create_session_from_schedule(db: Session, schedule: WeeklySchedule, target_date: date | None = None) -> ClassSession | None:
    target_date = target_date or date.today()
    start_at, late_at, close_at = build_schedule_datetimes(schedule, target_date)

    existing = (
        db.query(ClassSession)
        .filter(
            ClassSession.weekly_schedule_id == schedule.id,
            ClassSession.start_time >= datetime.combine(target_date, time.min),
            ClassSession.start_time <= datetime.combine(target_date, time.max),
        )
        .first()
    )
    if existing:
        return existing

    classroom = get_or_create_legacy_classroom(db, schedule.class_group)
    subject = get_or_create_legacy_subject(db, schedule.course)

    for active_session in db.query(ClassSession).filter(ClassSession.active.is_(True)).all():
        active_session.active = False
    db.commit()

    session = create_session(
        db,
        ClassSessionCreate(
            classroom_id=classroom.id,
            subject_id=subject.id,
            class_group_id=schedule.class_group_id,
            course_id=schedule.course_id,
            weekly_schedule_id=schedule.id,
            title=f"{schedule.course.code} - {schedule.class_group.code} ({target_date.isoformat()})",
            start_time=start_at,
            late_time=late_at,
            close_time=close_at,
            active=True,
            created_by=1,
        ),
    )
    prepare_session_attendance(db, session)
    return session


# Phase 16.2.1 academic code helpers
DEFAULT_DEPARTMENT_CODE = "CS"
DEFAULT_CLASS_LEVEL = "M4"
DEFAULT_YEAR_LEVEL = "Y3"
DEFAULT_GENERATION = "G27"


def build_class_group_code(
    department_code: str = DEFAULT_DEPARTMENT_CODE,
    class_level: str = DEFAULT_CLASS_LEVEL,
    year_level: str = DEFAULT_YEAR_LEVEL,
    generation: str = DEFAULT_GENERATION,
) -> str:
    return f"{department_code.strip().upper()}-{class_level.strip().upper()}-{year_level.strip().upper()}-{generation.strip().upper()}"


def generate_class_group_code(db, department_code: str = "CS", class_level: str = "M4", year_level: str = "Y3", generation: str = "G27") -> str:
    base_code = build_class_group_code(department_code, class_level, year_level, generation)

    existing = db.query(ClassGroup).filter(ClassGroup.code == base_code).first()
    if not existing:
        return base_code

    suffix = 2
    while True:
        candidate = f"{base_code}-{suffix}"
        existing = db.query(ClassGroup).filter(ClassGroup.code == candidate).first()
        if not existing:
            return candidate
        suffix += 1


def generate_course_code(db, course_name: str = "", preferred_prefix: str = "CSE") -> str:
    name = (course_name or "").strip().lower()

    if ".net" in name or "c#" in name or "csharp" in name or "c sharp" in name:
        prefix = "DOTNET"
    elif "iot" in name or "internet of things" in name:
        prefix = "IOT"
    elif "web" in name:
        prefix = "WEB"
    elif "database" in name:
        prefix = "DB"
    elif "network" in name:
        prefix = "NET"
    elif "ai" in name or "artificial intelligence" in name:
        prefix = "AI"
    elif "java" in name:
        prefix = "JAVA"
    elif "python" in name:
        prefix = "PY"
    elif "mobile" in name or "flutter" in name:
        prefix = "MOB"
    else:
        prefix = (preferred_prefix or "CSE").strip().upper()

    number = 301
    while True:
        candidate = f"{prefix}{number}"
        existing = db.query(Course).filter(Course.code == candidate).first()
        if not existing:
            return candidate
        number += 1

