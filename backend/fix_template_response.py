from pathlib import Path

files = [
    Path("app/routers/dashboard_router.py"),
    Path("app/routers/student_router.py"),
    Path("app/routers/session_router.py"),
    Path("app/routers/attendance_router.py"),
]

replacements = {
    'templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats})':
    'templates.TemplateResponse(request, "dashboard.html", {"stats": stats})',

    '''templates.TemplateResponse(
        "students/list.html",
        {"request": request, "students": get_students(db)},
    )''':
    '''templates.TemplateResponse(
        request,
        "students/list.html",
        {"students": get_students(db)},
    )''',

    '''templates.TemplateResponse(
        "sessions/list.html",
        {
            "request": request,
            "sessions": get_sessions(db),
            "classes": db.query(Classroom).order_by(Classroom.id).all(),
            "subjects": db.query(Subject).order_by(Subject.id).all(),
        },
    )''':
    '''templates.TemplateResponse(
        request,
        "sessions/list.html",
        {
            "sessions": get_sessions(db),
            "classes": db.query(Classroom).order_by(Classroom.id).all(),
            "subjects": db.query(Subject).order_by(Subject.id).all(),
        },
    )''',

    '''templates.TemplateResponse(
        "attendance/detail.html",
        {
            "request": request,
            "session": session,
            "records": get_attendance_records(db, session_id),
            "events": get_attendance_events(db, session_id),
            "statuses": list(AttendanceStatus),
        },
    )''':
    '''templates.TemplateResponse(
        request,
        "attendance/detail.html",
        {
            "session": session,
            "records": get_attendance_records(db, session_id),
            "events": get_attendance_events(db, session_id),
            "statuses": list(AttendanceStatus),
        },
    )''',
}

for file in files:
    if not file.exists():
        print(f"SKIP: {file} not found")
        continue

    text = file.read_text(encoding="utf-8")
    old_text = text

    for old, new in replacements.items():
        text = text.replace(old, new)

    file.write_text(text, encoding="utf-8")

    if text != old_text:
        print(f"FIXED: {file}")
    else:
        print(f"NO CHANGE: {file}")

print("Done. TemplateResponse fix completed.")
