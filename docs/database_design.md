# Database Design Notes

Main rule:

- `students` stores identity only.
- `attendance_records` stores final attendance status per student per session.
- `attendance_events` stores raw scan/recognition events.

Important constraint:

```text
UNIQUE(session_id, student_id)
```

This prevents duplicate final attendance records for the same student in the same session.
