from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Final Demo"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard/final-demo")
def final_demo_page(request: Request):
    demo_sections = [
        {
            "title": "1. Dashboard Overview",
            "goal": "Show total students, attendance summary, active session, and system status.",
            "url": "/dashboard",
        },
        {
            "title": "2. Student & QR Management",
            "goal": "Show student list, QR cards, printable QR, and face profile.",
            "url": "/dashboard/students",
        },
        {
            "title": "3. Session & Attendance",
            "goal": "Show session control, QR attendance, face attendance, manual override, and event logs.",
            "url": "/dashboard/sessions",
        },
        {
            "title": "4. Monitoring Workspace",
            "goal": "Show the only main live classroom stream with FACE attendance, YOLO detection, behavior, IoT, and optional recording.",
            "url": "/dashboard/monitoring-workspace",
        },
        {
            "title": "5. AI Monitoring",
            "goal": "Show phone usage, sleeping, leaving seat, hand raising, attention low, and student-level AI events.",
            "url": "/dashboard/ai-monitoring",
        },
        {
            "title": "6. IoT Monitoring",
            "goal": "Show Raspberry Pi / ESP32 devices, sensor readings, light/fan control, and auto-off rule.",
            "url": "/dashboard/iot-monitoring",
        },
        {
            "title": "7. Reports & Export",
            "goal": "Show attendance report, AI report, IoT report, automation report, and CSV export.",
            "url": "/dashboard/reports",
        },
    ]

    project_features = [
        "Student management",
        "QR attendance",
        "Face recognition attendance",
        "Monitoring Workspace with optional video recording",
        "Attendance event logging",
        "Teacher manual override",
        "AI behavior monitoring",
        "Student-level AI event logging",
        "IoT device and sensor monitoring",
        "Light/fan control simulation",
        "Auto light/fan off rule",
        "Reports and CSV export",
    ]

    defense_points = [
        {
            "question": "Why is attendance not stored directly in the Student table?",
            "answer": "Because attendance changes per class session. A student can be present in one session and absent in another, so attendance must be stored in AttendanceRecord linked to session and student.",
        },
        {
            "question": "Why do we keep event logs?",
            "answer": "Event logs make the system reliable and auditable. Every QR scan, face recognition result, AI event, and automation decision can be reviewed later.",
        },
        {
            "question": "How does face recognition connect with attendance?",
            "answer": "OpenCV recognizes a student ID, then sends it to FastAPI. FastAPI updates attendance using the same attendance workflow and logs the event as FACE.",
        },
        {
            "question": "How does IoT automation work?",
            "answer": "The system checks classroom occupancy from attendance records. If no students are detected for 5 minutes, the system can turn off lights and fans.",
        },
        {
            "question": "What makes this project scalable?",
            "answer": "The system separates models, routers, schemas, services, templates, AI modules, IoT APIs, and reports. This makes future Flutter app, Raspberry Pi, ESP32, YOLO, or MediaPipe integration easier.",
        },
    ]

    return templates.TemplateResponse(
        request,
        "demo/final_demo.html",
        {
            "request": request,
            "demo_sections": demo_sections,
            "project_features": project_features,
            "defense_points": defense_points,
        },
    )
