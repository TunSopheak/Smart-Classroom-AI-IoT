# Phase 16.2.2 Academic Lifecycle Safe Rules

## Principle

Academic records should not be hard-deleted after they are connected to history.

## Rules

- Class Group: edit or deactivate. Do not hard delete if sessions/enrollments exist.
- Course: edit or deactivate. Do not hard delete if schedules/sessions exist.
- Weekly Schedule: edit affects future sessions only. Existing sessions keep their history.
- Session: closed sessions can be archived. Active sessions must be closed before archive.
- Student Enrollment: remove from class means deactivate enrollment, not delete student.

## Added Routes

```text
POST /dashboard/class-setup/class-groups/{group_id}/update
POST /dashboard/class-setup/class-groups/{group_id}/deactivate
POST /dashboard/class-setup/courses/{course_id}/update
POST /dashboard/class-setup/courses/{course_id}/deactivate
POST /dashboard/class-setup/schedules/{schedule_id}/update
POST /dashboard/class-setup/schedules/{schedule_id}/deactivate
POST /dashboard/class-setup/enrollments/{enrollment_id}/deactivate
POST /dashboard/sessions/{session_id}/archive
```
