from pathlib import Path

detail_path = Path("app/templates/students/detail.html")
text = detail_path.read_text(encoding="utf-8")

if 'href="/dashboard/students/{{ student.id }}/face-profile"' not in text:
    text = text.replace(
        '<a class="button" href="/dashboard/students/{{ student.id }}/print-qr">Print QR</a>',
        '<a class="button" href="/dashboard/students/{{ student.id }}/print-qr">Print QR</a>\n        <a class="button secondary-button" href="/dashboard/students/{{ student.id }}/face-profile">Face Profile</a>',
    )

detail_path.write_text(text, encoding="utf-8")

print("Step 4 done: Face Profile button added.")
