from pathlib import Path

ROOT = Path(".")
BACKEND = ROOT / "backend"

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, text):
    Path(path).write_text(text, encoding="utf-8")
    print(f"Updated: {path}")

# 1) Add stronger schedule lifecycle routes
router_path = BACKEND / "app/routers/academic_lifecycle_router.py"
router = read(router_path)

if "quote_plus" not in router:
    router = "from urllib.parse import quote_plus\n" + router

if "validate_weekly_schedule_rule" not in router:
    router = "from app.services.academic_rules import validate_weekly_schedule_rule\n" + router

if "def redirect_class_setup_v2" not in router:
    router += r'''


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
'''

write(router_path, router)

# 2) Add a new clean schedule manager card into class setup page
tpl_path = BACKEND / "app/templates/class_setup/index.html"
tpl = read(tpl_path)

manager = r'''

<section id="scheduleManager" class="card schedule-manager-card">
    <div class="section-title-row schedule-manager-header">
        <div>
            <p class="eyebrow">Schedule Control</p>
            <h2>Weekly Schedule Manager</h2>
            <p class="muted">
                Manage class timetable safely. Same class cannot have overlapping schedules on the same day.
            </p>
        </div>
        <a class="btn btn-secondary btn-sm" href="/dashboard/sessions">Open Sessions</a>
    </div>

    <div class="schedule-rule-note">
        <strong>Conflict rule:</strong>
        Same class + same day + overlapping time is blocked. Updates affect future sessions only; existing sessions keep their history.
    </div>

    {% if request.query_params.get("message") %}
    <div class="success-note compact-note">{{ request.query_params.get("message") }}</div>
    {% endif %}

    <form method="post" action="/dashboard/class-setup/schedules/manage-create" class="schedule-manager-form">
        <label>
            <span>Class</span>
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

        <label>
            <span>Course</span>
            <select name="course_id" required>
                {% for course in courses|default([]) %}
                {% if course.active %}
                <option value="{{ course.id }}">{{ course.code }} - {{ course.name }}</option>
                {% endif %}
                {% endfor %}
            </select>
        </label>

        <label>
            <span>Day</span>
            <select name="weekday" required>
                <option value="0">Monday</option>
                <option value="1">Tuesday</option>
                <option value="2">Wednesday</option>
                <option value="3">Thursday</option>
                <option value="4">Friday</option>
                <option value="5">Saturday</option>
                <option value="6">Sunday</option>
            </select>
        </label>

        <label>
            <span>Start</span>
            <input type="time" name="start_time" value="06:00" required>
        </label>

        <label>
            <span>End</span>
            <input type="time" name="end_time" value="08:00" required>
        </label>

        <label>
            <span>Late after</span>
            <input type="number" min="0" name="late_after_minutes" value="15" required>
        </label>

        <label>
            <span>Location</span>
            <input name="location" value="Smart Classroom Lab" placeholder="Room / Lab">
        </label>

        <button class="btn btn-primary" type="submit">Add Schedule</button>
    </form>

    {% set schedule_list = weekly_schedules|default(schedules|default([])) %}

    <div class="schedule-manager-list">
        {% for schedule in schedule_list %}
        <article class="schedule-item {% if not schedule.active %}is-inactive{% endif %}">
            <div class="schedule-main">
                <div class="schedule-code">
                    <strong>
                        {{ schedule.class_group.code if schedule.class_group else schedule.class_group_id }}
                    </strong>
                    <span class="badge">{{ schedule.course.code if schedule.course else schedule.course_id }}</span>
                </div>

                <div class="schedule-time">
                    <strong>
                        {% if schedule.weekday == 0 %}Monday{% elif schedule.weekday == 1 %}Tuesday{% elif schedule.weekday == 2 %}Wednesday{% elif schedule.weekday == 3 %}Thursday{% elif schedule.weekday == 4 %}Friday{% elif schedule.weekday == 5 %}Saturday{% else %}Sunday{% endif %}
                    </strong>
                    <span>{{ schedule.start_time }} - {{ schedule.end_time }}</span>
                </div>

                <div class="schedule-location">
                    <span>{{ schedule.location or "No location" }}</span>
                    <small>Late after {{ schedule.late_after_minutes or 15 }} min</small>
                </div>

                <div class="schedule-status">
                    {% if schedule.active %}
                    <span class="badge success-badge">Active</span>
                    {% else %}
                    <span class="badge muted-badge">Inactive</span>
                    {% endif %}
                </div>

                <div class="schedule-actions">
                    <details class="inline-edit-details">
                        <summary class="btn btn-secondary btn-sm">Edit</summary>

                        <form method="post" action="/dashboard/class-setup/schedules/{{ schedule.id }}/update" class="schedule-edit-form">
                            <label>
                                <span>Class</span>
                                <select name="class_group_id" required>
                                    {% for group in class_groups|default([]) %}
                                    <option value="{{ group.id }}" {% if group.id == schedule.class_group_id %}selected{% endif %}>
                                        {{ group.code }}
                                    </option>
                                    {% endfor %}
                                </select>
                            </label>

                            <label>
                                <span>Course</span>
                                <select name="course_id" required>
                                    {% for course in courses|default([]) %}
                                    <option value="{{ course.id }}" {% if course.id == schedule.course_id %}selected{% endif %}>
                                        {{ course.code }}
                                    </option>
                                    {% endfor %}
                                </select>
                            </label>

                            <label>
                                <span>Day</span>
                                <select name="weekday">
                                    <option value="0" {% if schedule.weekday == 0 %}selected{% endif %}>Monday</option>
                                    <option value="1" {% if schedule.weekday == 1 %}selected{% endif %}>Tuesday</option>
                                    <option value="2" {% if schedule.weekday == 2 %}selected{% endif %}>Wednesday</option>
                                    <option value="3" {% if schedule.weekday == 3 %}selected{% endif %}>Thursday</option>
                                    <option value="4" {% if schedule.weekday == 4 %}selected{% endif %}>Friday</option>
                                    <option value="5" {% if schedule.weekday == 5 %}selected{% endif %}>Saturday</option>
                                    <option value="6" {% if schedule.weekday == 6 %}selected{% endif %}>Sunday</option>
                                </select>
                            </label>

                            <label>
                                <span>Start</span>
                                <input type="time" name="start_time" value="{{ schedule.start_time }}" required>
                            </label>

                            <label>
                                <span>End</span>
                                <input type="time" name="end_time" value="{{ schedule.end_time }}" required>
                            </label>

                            <label>
                                <span>Late</span>
                                <input type="number" min="0" name="late_after_minutes" value="{{ schedule.late_after_minutes or 15 }}">
                            </label>

                            <label>
                                <span>Location</span>
                                <input name="location" value="{{ schedule.location or '' }}">
                            </label>

                            <button class="btn btn-primary btn-sm" type="submit">Save Changes</button>
                        </form>
                    </details>

                    {% if schedule.active %}
                    <form method="post" action="/dashboard/class-setup/schedules/{{ schedule.id }}/deactivate">
                        <button class="btn btn-secondary btn-sm" type="submit">Deactivate</button>
                    </form>
                    {% else %}
                    <form method="post" action="/dashboard/class-setup/schedules/{{ schedule.id }}/reactivate">
                        <button class="btn btn-primary btn-sm" type="submit">Reactivate</button>
                    </form>
                    {% endif %}

                    <form method="post" action="/dashboard/class-setup/schedules/{{ schedule.id }}/safe-delete"
                          onsubmit="return confirm('Safe delete this schedule? If it has session history, it will be deactivated instead.');">
                        <button class="btn btn-danger btn-sm" type="submit">Safe Delete</button>
                    </form>
                </div>
            </div>
        </article>
        {% else %}
        <div class="empty-state">
            <strong>No schedule yet.</strong>
            <p>Add a schedule above to create reusable class timetable.</p>
        </div>
        {% endfor %}
    </div>
</section>
'''

if "Weekly Schedule Manager" not in tpl:
    if "Auto Sessions from Weekly Schedule" in tpl:
        tpl = tpl.replace('<section', manager + "\n<section", 1) if False else tpl
        # Better: insert before Auto Sessions section heading
        idx = tpl.find("Auto Sessions from Weekly Schedule")
        section_start = tpl.rfind("<section", 0, idx)
        if section_start != -1:
            tpl = tpl[:section_start] + manager + "\n" + tpl[section_start:]
        else:
            tpl = tpl + manager
    elif "{% endblock %}" in tpl:
        tpl = tpl.replace("{% endblock %}", manager + "\n{% endblock %}", 1)
    else:
        tpl += manager

write(tpl_path, tpl)

# 3) Add CSS
css_path = BACKEND / "app/static/css/styles.css"
css = read(css_path)

css_patch = r"""

/* Phase 16.2.4 Schedule Manager UX */
.schedule-manager-card {
    margin-top: 1rem;
}

.schedule-manager-header {
    gap: 1rem;
}

.schedule-rule-note {
    margin: 0.85rem 0 1rem;
    padding: 0.8rem 0.9rem;
    border: 1px solid #bfdbfe;
    border-radius: 16px;
    background: #eff6ff;
    color: #1e3a8a;
    font-size: 0.88rem;
    line-height: 1.45;
}

.schedule-manager-form {
    display: grid;
    grid-template-columns: 1.5fr 1.35fr 0.9fr 0.72fr 0.72fr 0.72fr 1.15fr auto;
    gap: 0.75rem;
    align-items: end;
    padding: 1rem;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    background: #f8fafc;
}

.schedule-manager-form label,
.schedule-edit-form label {
    display: grid;
    gap: 0.35rem;
    min-width: 0;
}

.schedule-manager-form label span,
.schedule-edit-form label span {
    color: #64748b;
    font-size: 0.74rem;
    font-weight: 900;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.schedule-manager-form input,
.schedule-manager-form select,
.schedule-edit-form input,
.schedule-edit-form select {
    min-width: 0;
    height: 40px;
    font-size: 0.88rem !important;
}

.schedule-manager-list {
    display: grid;
    gap: 0.75rem;
    margin-top: 1rem;
}

.schedule-item {
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    background: #ffffff;
    box-shadow: 0 12px 35px rgba(15, 23, 42, 0.04);
    overflow: hidden;
}

.schedule-item.is-inactive {
    background: #f8fafc;
    opacity: 0.82;
}

.schedule-main {
    display: grid;
    grid-template-columns: 1.35fr 1.2fr 1.25fr 0.75fr auto;
    gap: 0.9rem;
    align-items: center;
    padding: 0.9rem 1rem;
}

.schedule-code,
.schedule-time,
.schedule-location {
    display: grid;
    gap: 0.25rem;
    min-width: 0;
}

.schedule-code strong,
.schedule-time strong {
    font-size: 0.92rem;
    color: #0f172a;
}

.schedule-time span,
.schedule-location span,
.schedule-location small {
    font-size: 0.82rem;
    color: #64748b;
}

.schedule-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    justify-content: flex-end;
    align-items: center;
}

.inline-edit-details {
    position: relative;
}

.inline-edit-details > summary {
    list-style: none;
    cursor: pointer;
}

.inline-edit-details > summary::-webkit-details-marker {
    display: none;
}

.schedule-edit-form {
    position: absolute;
    right: 0;
    top: calc(100% + 0.5rem);
    z-index: 20;
    width: min(760px, 88vw);
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.7rem;
    padding: 1rem;
    border: 1px solid #bfdbfe;
    border-radius: 18px;
    background: #ffffff;
    box-shadow: 0 24px 80px rgba(15, 23, 42, 0.16);
}

.schedule-edit-form button {
    align-self: end;
}

.empty-state {
    padding: 1rem;
    border: 1px dashed #cbd5e1;
    border-radius: 16px;
    color: #64748b;
    background: #f8fafc;
}

.empty-state p {
    margin-top: 0.25rem;
}

@media (max-width: 1260px) {
    .schedule-manager-form {
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .schedule-main {
        grid-template-columns: 1fr 1fr;
    }

    .schedule-actions {
        justify-content: flex-start;
        grid-column: 1 / -1;
    }
}

@media (max-width: 720px) {
    .schedule-manager-form,
    .schedule-edit-form {
        grid-template-columns: 1fr;
    }

    .schedule-main {
        grid-template-columns: 1fr;
    }

    .schedule-actions {
        display: grid;
        grid-template-columns: 1fr;
    }

    .schedule-actions .btn,
    .schedule-actions button {
        width: 100%;
    }
}
"""

if "Phase 16.2.4 Schedule Manager UX" not in css:
    css += css_patch
    write(css_path, css)

# 4) Add JS to hide the old Weekly Schedule card if the new manager exists
js_path = BACKEND / "app/static/js/product_workflow_polish.js"
js = read(js_path) if js_path.exists() else ""

js_patch = r"""

// Phase 16.2.4 Schedule Manager UX
(function () {
    function text(el) {
        return (el && el.textContent || "").replace(/\s+/g, " ").trim();
    }

    function hideOldWeeklyScheduleCard() {
        if (!window.location.pathname.includes("/dashboard/class-setup")) return;

        const manager = document.getElementById("scheduleManager");
        if (!manager) return;

        const headings = Array.from(document.querySelectorAll("h2, h3"));
        headings.forEach(function (heading) {
            const value = text(heading).toLowerCase();

            if (value === "weekly schedule") {
                const card = heading.closest(".card") || heading.closest("section");
                if (card && card.id !== "scheduleManager") {
                    card.style.display = "none";
                }
            }
        });
    }

    document.addEventListener("DOMContentLoaded", hideOldWeeklyScheduleCard);
})();
"""

if "Phase 16.2.4 Schedule Manager UX" not in js:
    js += js_patch
    write(js_path, js)

print("")
print("DONE: Phase 16.2.4 Schedule Manager UX patch applied.")
