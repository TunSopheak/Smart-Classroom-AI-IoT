from pathlib import Path

attendance_template = Path("app/templates/attendance/detail.html")
text = attendance_template.read_text(encoding="utf-8")

if "Face Recognition Prototype" not in text:
    insert = r'''
<section class="panel face-panel">
    <h2>Face Recognition Prototype</h2>
    <p class="muted">This simulates face recognition output. Later, OpenCV will call the same attendance workflow automatically.</p>

    {% if session.active %}
        <div class="quick-face-list">
            {% for record in records %}
                <form action="/dashboard/attendance/face-simulate" method="post">
                    <input type="hidden" name="session_id" value="{{ session.id }}">
                    <input type="hidden" name="student_id" value="{{ record.student.id }}">
                    <input type="hidden" name="confidence" value="0.86">
                    <button class="face-chip" type="submit">Face: {{ record.student.stu_id }}</button>
                </form>
            {% endfor %}
        </div>
    {% else %}
        <p class="muted">This session is closed. Reopen it first if you need to test face recognition attendance.</p>
    {% endif %}
</section>
'''
    text = text.replace(
        '<section class="panel">\n    <h2>Attendance Records</h2>',
        insert + '\n<section class="panel">\n    <h2>Attendance Records</h2>'
    )

attendance_template.write_text(text, encoding="utf-8")

print("Step 5 done: Face Recognition Prototype panel added.")
