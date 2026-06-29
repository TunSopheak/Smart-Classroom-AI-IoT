# Phase 13 Authentication and Role-Based Access

## Goal

Protect sensitive product pages with login and demo role-based access.

## Demo Accounts

```text
admin / admin123
teacher / teacher123
viewer / viewer123
```

## Roles

### Admin

Full access to all pages including:

- Product Settings
- System Health
- Admin Storage
- Privacy
- Camera Monitoring
- Reports

### Teacher

Access to teaching workflows:

- Dashboard
- Students
- Sessions
- AI Monitoring
- Camera Monitoring
- IoT Monitoring
- Reports
- Final Demo

Teacher cannot access admin-only pages such as Admin Storage and Product Settings.

### Viewer

Limited read/demo access:

- Dashboard
- Final Demo
- Privacy

## Protected Data

This phase protects:

- Camera recordings
- Admin storage management
- Reports
- Product settings
- System health
- Student and attendance pages

## Product Note

This is demo authentication for project defense. A production version should use hashed passwords, database users, HTTPS, password reset, and stronger session management.
