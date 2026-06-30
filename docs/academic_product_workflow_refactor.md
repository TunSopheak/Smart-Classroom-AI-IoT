# Phase 16 Academic Product Workflow Refactor

## Phase 16.1

This phase cleans the product workflow without changing the database schema.

### Changes

- One-click Start Monitoring / Stop Monitoring command bar.
- Monitoring starts camera, auto attendance, and behavior prototype together where controls exist.
- Recording remains optional because of privacy and storage impact.
- Session attendance page becomes review-first.
- Duplicate QR/Face prototype controls are hidden from attendance review pages.
- Privacy page is available to authenticated roles.
- Tables, device names, reports, AI events, filenames, and readiness checklist are compacted.

## Next Phase 16.2

Recommended next product architecture:

- Class Groups
- Courses / Subjects
- Weekly Class Schedules
- Auto-generated sessions from schedule
- Auto-generated student codes
- Student membership by class group
