from pathlib import Path

path = Path("app/templates/attendance/detail.html")
text = path.read_text(encoding="utf-8")

text = text.replace(
    "{{ record.confidence or '-' }}",
    "{{ '%.2f'|format(record.confidence) if record.confidence is not none else '-' }}"
)

text = text.replace(
    "{{ event.confidence if event.confidence is not none else '-' }}",
    "{{ '%.2f'|format(event.confidence) if event.confidence is not none else '-' }}"
)

path.write_text(text, encoding="utf-8")

print("Step 2 done: attendance confidence display cleaned.")
