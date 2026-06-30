# Final Demo Checklist

Use this checklist before presenting the Smart Classroom AI Monitoring IoT project.

## Before Demo Setup

- Charge the laptop and keep the charger connected.
- Use a clean table with enough light for face recognition.
- Close apps that may use the camera, such as Zoom, Teams, OBS, or browser camera tabs.
- Use Chrome or Edge for the dashboard.
- Keep one trained student face ready for the FACE attendance demo.
- Prepare one book and one phone for YOLO object detection.
- Prepare QR code backup for at least one student.
- Do not move or delete model files, face model files, recordings, datasets, or the database.

## Start Backend Command

Open PowerShell:

```powershell
cd D:\IT\IT-RUPP\Y3\CN\Project\smart-classroom-ai-iot\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Open the system:

```text
http://127.0.0.1:8000/login
```

Demo accounts:

```text
admin / admin123
teacher / teacher123
viewer / viewer123
```

## Confirm Active Session

- Login as `teacher` or `admin`.
- Open `Sessions`.
- Confirm there is one active class session.
- If no session is active, create or activate a demo session.
- Open:

```text
http://127.0.0.1:8000/dashboard/monitoring-workspace
```

## Confirm YOLO Model Exists Locally

Check that this file exists:

```text
backend/ai_module/object_detection/models/yolov8n.onnx
```

Important: this file is local only and ignored by Git. Do not commit it.

## Confirm Camera Works

- Make sure no other app is using the camera.
- Open Monitoring Workspace.
- Click `Start Monitoring`.
- Confirm the live classroom camera appears.
- Confirm the overlay shows compact chips:
  - FACE ON
  - YOLO ON
  - BEHAVIOR ON
  - SESSION #id

## Demo Steps

1. Login as teacher or admin.
2. Open `Class Setup` and briefly show class group, course, students, and enrollment.
3. Open `Monitoring Workspace`.
4. Select the active session.
5. Explain the one-click control.
6. Click `Start Monitoring`.
7. Show the live camera stream.
8. Show a trained face and explain FACE attendance.
9. If confidence is high, point out that attendance is marked once.
10. Show a book and wait for the BOOK label.
11. Show a phone and wait for the PHONE label.
12. Point out object detection status updates.
13. Explain behavior monitoring and phone usage alert.
14. Explain IoT Auto Control:
    - Occupancy comes from person count, face count, and attendance.
    - If no occupancy is detected for 5 minutes, simulated light/fan relays turn off.
15. Explain recording privacy:
    - Recording is manual and optional.
    - The system does not record automatically.
16. Open Reports and show attendance/report output.
17. Return to Monitoring Workspace.
18. Click `Stop Monitoring`.
19. Confirm statuses return to stopped or idle.

## Backup Plan If Face Recognition Fails

- Say clearly: "FACE recognition is confidence-gated, so if the model is not confident, it will not mark the wrong student."
- Use QR backup attendance:

```text
Monitoring Workspace -> QR Backup Panel -> Open Camera QR Scanner
```

- Scan or paste the student's QR code.
- Explain that QR is the safe fallback for low light, untrained students, or low confidence.

## Backup Plan If YOLO Is Slow

- Wait 2 to 5 seconds because YOLO runs on interval/cache to keep the stream smooth.
- Hold the phone or book clearly in front of the camera.
- Use good lighting and avoid fast movement.
- Explain: "YOLO is not running every frame because the system protects camera performance."
- If needed, open:

```text
http://127.0.0.1:8000/dashboard/object-detection
```

- Say this page is `Debug / Model Test Only`; the real product uses Monitoring Workspace.

## Backup Plan If Camera Is Busy

- Stop Monitoring.
- Close Zoom, Teams, OBS, browser camera tabs, or other webcam apps.
- Refresh the dashboard.
- Click Start Monitoring again.
- If still busy, restart the backend server and retry.
- Do not open multiple camera stream pages at the same time during the demo.

## What Not To Click During Demo

- Do not click advanced/manual controls unless needed for backup.
- Do not open many camera pages at the same time.
- Do not start the Object Detection debug stream while Monitoring Workspace is already using the camera, unless it is part of the backup plan.
- Do not click admin cleanup or delete recording buttons.
- Do not retrain the face model during the live demo.
- Do not edit database, model, recording, or dataset files.
- Do not commit during the demo.

## Final Git Clean Check Commands

Before final presentation:

```powershell
git status --short
git branch --show-current
```

Check ignored privacy/model paths are not staged:

```powershell
git status --short --ignored
```

Do not commit these files or folders:

```text
backend/ai_module/object_detection/models/*.onnx
backend/ai_module/object_detection/models/*.pt
backend/app/static/recordings/
backend/ai_module/face_recognition/datasets/
backend/ai_module/face_recognition/models/
*.db
*.sqlite
*.sqlite3
```
