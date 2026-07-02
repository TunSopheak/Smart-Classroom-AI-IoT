# Final Demo Checklist

Use this checklist before presenting the Smart Classroom with AI Monitoring - IoT Project.

## Before Presentation

- Charge the laptop or Raspberry Pi power source.
- Connect to a stable Wi-Fi/LAN network.
- Use good room lighting.
- Close other camera apps such as Zoom, Teams, OBS, or browser camera tabs.
- Prepare at least one trained student face.
- Prepare one QR code backup.
- Prepare one phone and one book for object detection.
- Confirm the local database is ready.
- Confirm private files are not staged in Git.

## Start Local Demo

```powershell
cd backend
$env:SMART_CLASSROOM_DEVICE_API_KEY="smart-classroom-demo-device-key"
python -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/dashboard
```

## Start LAN Demo

```powershell
cd backend
$env:SMART_CLASSROOM_DEVICE_API_KEY="smart-classroom-demo-device-key"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open from another device:

```text
http://<host-ip>:8000/dashboard
```

## Demo Pages

```text
http://127.0.0.1:8000/dashboard
http://127.0.0.1:8000/dashboard/monitoring-workspace
http://127.0.0.1:8000/dashboard/face-training
http://127.0.0.1:8000/dashboard/reports
```

## Presentation Flow

1. Explain the project problem: classroom attendance and monitoring can be time-consuming.
2. Open the dashboard.
3. Show the Product Center or Class Setup page.
4. Open Monitoring Workspace.
5. Start monitoring.
6. Demonstrate face attendance with a trained student.
7. Demonstrate QR attendance as backup.
8. Demonstrate phone/book/person object detection.
9. Explain Raspberry Pi 5 and IoT target architecture.
10. Open Reports.
11. Stop monitoring.
12. Explain privacy and current MVP limitations honestly.

## Backup Plan

- If face recognition is not confident, use QR attendance.
- If object detection is slow, wait a few seconds and hold the object clearly.
- If the camera is busy, close other camera apps and restart monitoring.
- If LAN access fails, present from `127.0.0.1` on the host machine.

## Git Safety Check

Run:

```powershell
git status --short
git status --short --ignored
```

Do not commit:

- `.env`
- `smart_classroom.db`
- dataset images
- trained models
- recordings
- private face data
- generated QR/media if sensitive

## Final Message To Audience

This is an MVP/final demo version. It shows the main idea and workflow of a smart classroom system. A real public deployment would need stronger security, privacy, hardware testing, and production infrastructure.
