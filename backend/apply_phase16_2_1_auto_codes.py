from pathlib import Path
import re

ROOT = Path(".")
BACKEND = ROOT / "backend"

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, text):
    Path(path).write_text(text, encoding="utf-8")
    print(f"Updated: {path}")

academic_service_path = BACKEND / "app/services/academic_service.py"
text = read(academic_service_path)

# Add helpers if missing
helpers = r'''

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


def generate_course_code(db, course_name: str = "", preferred_prefix: str = "IOT") -> str:
    name = (course_name or "").strip().lower()

    if "iot" in name or "internet of things" in name:
        prefix = "IOT"
    elif "network" in name:
        prefix = "NET"
    elif "database" in name:
        prefix = "DB"
    elif "web" in name:
        prefix = "WEB"
    elif "ai" in name or "artificial intelligence" in name:
        prefix = "AI"
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

if "def build_class_group_code" not in text:
    text += helpers

# Update seed values if present
text = text.replace('"M4-Y3-G1"', '"CS-M4-Y3-G27"')
text = text.replace("'M4-Y3-G1'", "'CS-M4-Y3-G27'")
text = text.replace('"M4 Year 3 Group 1"', '"Computer Science M4 Year 3 Generation 27"')
text = text.replace("'M4 Year 3 Group 1'", "'Computer Science M4 Year 3 Generation 27'")

write(academic_service_path, text)

# Patch class_setup_router to auto-generate missing class/course codes
router_path = BACKEND / "app/routers/class_setup_router.py"
router = read(router_path)

# Ensure imports include helpers
if "generate_class_group_code" not in router:
    router = router.replace(
        "from app.services.academic_service import",
        "from app.services.academic_service import",
        1
    )

    import_match = re.search(r"from app\.services\.academic_service import \((.*?)\)", router, flags=re.S)
    if import_match:
        body = import_match.group(1)
        add_items = []
        if "generate_class_group_code" not in body:
            add_items.append("generate_class_group_code")
        if "generate_course_code" not in body:
            add_items.append("generate_course_code")
        if add_items:
            body = body.rstrip() + ",\n    " + ",\n    ".join(add_items) + "\n"
            router = router[:import_match.start(1)] + body + router[import_match.end(1):]
    else:
        router = router.replace(
            "from app.database.database import",
            "from app.services.academic_service import generate_class_group_code, generate_course_code\nfrom app.database.database import",
            1
        )

# Make class group code optional in form route if possible
router = router.replace("code: str = Form(...)", "code: str = Form('')")
router = router.replace("course_code: str = Form(...)", "course_code: str = Form('')")

# Common variable patch patterns
router = router.replace("code=code.strip()", "code=(code.strip() or generate_class_group_code(db))")
router = router.replace("code=course_code.strip()", "code=(course_code.strip() or generate_course_code(db, name))")
router = router.replace("code=course_code", "code=(course_code.strip() or generate_course_code(db, name))")

write(router_path, router)

# Patch class setup template labels/placeholders
template_path = BACKEND / "app/templates/class_setup/index.html"
tpl = read(template_path)

tpl = tpl.replace("M4-Y3-G1", "CS-M4-Y3-G27")
tpl = tpl.replace("M4 Year 3 Group 1", "Computer Science M4 Year 3 Generation 27")

tpl = tpl.replace('placeholder="M4-Y3-G1"', 'placeholder="Auto: CS-M4-Y3-G27"')
tpl = tpl.replace('placeholder="IOT301"', 'placeholder="Auto: IOT301"')
tpl = tpl.replace('placeholder="Class code"', 'placeholder="Auto: CS-M4-Y3-G27"')
tpl = tpl.replace('placeholder="Course code"', 'placeholder="Auto: IOT301"')

if "Class code is auto-generated" not in tpl:
    tpl = tpl.replace(
        "Add Class Group",
        "Add Class Group",
        1
    )
    tpl = tpl.replace(
        "</form>",
        '<p class="muted small-note">Class code is auto-generated if left empty. Example: CS-M4-Y3-G27 = Computer Science, M4, Year 3, Generation 27.</p>\n</form>',
        1
    )

if "Course code is auto-generated" not in tpl:
    second_form_pos = tpl.find("</form>", tpl.find("Add Course"))
    if second_form_pos != -1:
        tpl = tpl[:second_form_pos] + '<p class="muted small-note">Course code is auto-generated if left empty. Example: IOT301.</p>\n' + tpl[second_form_pos:]

write(template_path, tpl)

# Patch sessions template text
sessions_path = BACKEND / "app/templates/sessions/list.html"
sessions = read(sessions_path)
sessions = sessions.replace("M4-Y3-G1", "CS-M4-Y3-G27")
sessions = sessions.replace("M4 Year 3 Group 1", "Computer Science M4 Year 3 Generation 27")
write(sessions_path, sessions)

# Patch README/doc mention if exists
for p in [ROOT / "README.md", ROOT / "docs/academic_product_workflow_refactor.md"]:
    if p.exists():
        content = read(p)
        content = content.replace("M4-Y3-G1", "CS-M4-Y3-G27")
        content = content.replace("M4 Year 3 Group 1", "Computer Science M4 Year 3 Generation 27")
        write(p, content)

# Add small CSS note style
css_path = BACKEND / "app/static/css/styles.css"
css = read(css_path)

if "Phase 16.2.1 academic auto code polish" not in css:
    css += r"""

/* Phase 16.2.1 academic auto code polish */
.small-note {
    margin-top: 0.55rem;
    font-size: 0.82rem;
    color: #64748b;
}

.code-meaning-note {
    padding: 0.75rem 0.9rem;
    border: 1px solid #dbeafe;
    border-radius: 14px;
    background: #eff6ff;
    color: #1e3a8a;
    font-size: 0.88rem;
    line-height: 1.5;
}
"""
    write(css_path, css)

# Patch seed file if it contains old values
seed_path = BACKEND / "app/database/seed.py"
if seed_path.exists():
    seed = read(seed_path)
    seed = seed.replace('"M4-Y3-G1"', '"CS-M4-Y3-G27"')
    seed = seed.replace("'M4-Y3-G1'", "'CS-M4-Y3-G27'")
    seed = seed.replace('"M4 Year 3 Group 1"', '"Computer Science M4 Year 3 Generation 27"')
    seed = seed.replace("'M4 Year 3 Group 1'", "'Computer Science M4 Year 3 Generation 27'")
    write(seed_path, seed)

print("")
print("DONE: Phase 16.2.1 code auto-generation patch applied.")
