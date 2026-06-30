from pathlib import Path
import re

ROOT = Path(".")
BACKEND = ROOT / "backend"

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, text):
    Path(path).write_text(text, encoding="utf-8")
    print(f"Updated: {path}")

# 1) Fix course code generator in academic_service.py
service_path = BACKEND / "app/services/academic_service.py"
text = read(service_path)

new_generate_course_code = r'''def generate_course_code(db, course_name: str = "", preferred_prefix: str = "CSE") -> str:
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
'''

if "def generate_course_code" in text:
    text = re.sub(
        r"def generate_course_code\(.*?(?=\n\ndef |\Z)",
        new_generate_course_code + "\n",
        text,
        flags=re.S,
    )
else:
    text += "\n\n" + new_generate_course_code + "\n"

write(service_path, text)

# 2) Fix course creation route so it uses generate_course_code, not class group code
router_path = BACKEND / "app/routers/class_setup_router.py"
router = read(router_path)

# Ensure imports
if "generate_course_code" not in router:
    if "from app.services.academic_service import" in router:
        router = router.replace(
            "from app.services.academic_service import",
            "from app.services.academic_service import generate_course_code,",
            1,
        )
    else:
        router = "from app.services.academic_service import generate_course_code\n" + router

if "RedirectResponse" not in router:
    router = "from fastapi.responses import RedirectResponse\n" + router

# Find the course creation route block in class_setup_router.py
blocks = re.split(r"(?=\n@router\.post)", router)
new_blocks = []

replacement_done = False

for block in blocks:
    lower = block.lower()

    is_course_create_block = (
        "@router.post" in block
        and "course" in lower
        and "Course(" in block
        and "{course_id}" not in block
        and "deactivate" not in lower
        and "update" not in lower
    )

    if is_course_create_block:
        decorator_match = re.search(r"@router\.post\([^\n]+\)", block)
        decorator = decorator_match.group(0) if decorator_match else '@router.post("/dashboard/class-setup/courses/create")'

        fixed_block = f'''
{decorator}
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
'''
        new_blocks.append(fixed_block)
        replacement_done = True
    else:
        new_blocks.append(block)

router = "".join(new_blocks)

if not replacement_done:
    print("WARNING: Could not auto-replace course create route. Please send class_setup_router.py if course add still fails.")

write(router_path, router)

# 3) Fix wrong existing course code in database: CS-M4-Y3-G27-2 -> WEB301/DOTNET301/etc.
cleanup_path = BACKEND / "fix_bad_course_codes.py"
cleanup = r'''
from app.database.database import SessionLocal
from app.models.academic import Course

def prefix_for(name):
    value = (name or "").strip().lower()

    if ".net" in value or "c#" in value or "csharp" in value or "c sharp" in value:
        return "DOTNET"
    if "iot" in value or "internet of things" in value:
        return "IOT"
    if "web" in value:
        return "WEB"
    if "database" in value:
        return "DB"
    if "network" in value:
        return "NET"
    if "ai" in value or "artificial intelligence" in value:
        return "AI"
    if "java" in value:
        return "JAVA"
    if "python" in value:
        return "PY"
    if "mobile" in value or "flutter" in value:
        return "MOB"

    return "CSE"

def next_code(db, prefix, ignore_id=None):
    number = 301

    while True:
        candidate = f"{prefix}{number}"
        query = db.query(Course).filter(Course.code == candidate)

        if ignore_id is not None:
            query = query.filter(Course.id != ignore_id)

        if not query.first():
            return candidate

        number += 1

db = SessionLocal()

try:
    bad_courses = (
        db.query(Course)
        .filter(Course.code.like("CS-M4-Y3-G27%"))
        .all()
    )

    if not bad_courses:
        print("No bad course codes found.")
    else:
        for course in bad_courses:
            prefix = prefix_for(course.name)
            new_code = next_code(db, prefix, ignore_id=course.id)
            print(f"Fixing course code: {course.code} -> {new_code} ({course.name})")
            course.code = new_code

        db.commit()

    print("")
    print("Current courses:")
    for course in db.query(Course).order_by(Course.id).all():
        print(course.id, course.code, course.name, "active=", course.active)

finally:
    db.close()
'''
cleanup_path.write_text(cleanup, encoding="utf-8")
print(f"Created: {cleanup_path}")
