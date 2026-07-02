# Demo Guide

This guide helps present the Smart Classroom with AI Monitoring - IoT Project as a final demo or portfolio project.

## Recommended Demo Mode

Use a local or LAN demo. This keeps the project private, avoids cloud setup risk, and still shows the system working like a classroom product.

Recommended pages:

```text
http://127.0.0.1:8000/dashboard
http://127.0.0.1:8000/dashboard/monitoring-workspace
http://127.0.0.1:8000/dashboard/face-training
http://127.0.0.1:8000/dashboard/reports
```

## Before the Demo

- Prepare a laptop or Raspberry Pi 5 with the project installed.
- Use good lighting for face recognition.
- Close other camera apps such as Zoom, Teams, OBS, or browser camera tabs.
- Prepare at least one trained student face.
- Prepare one QR code backup for the same student.
- Prepare a phone and a book for object detection.
- Confirm that local database, datasets, and trained models are available on the demo machine.

## Start the Backend

```powershell
cd backend
$env:SMART_CLASSROOM_DEVICE_API_KEY="smart-classroom-demo-device-key"
python -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/dashboard
```

## LAN Demo

Start the backend with LAN access:

```powershell
cd backend
$env:SMART_CLASSROOM_DEVICE_API_KEY="smart-classroom-demo-device-key"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

From another device on the same network, open:

```text
http://<host-ip>:8000/dashboard
```

Replace `<host-ip>` with the IP address of the laptop or Raspberry Pi running the backend.

## Suggested Demo Flow

1. Open the dashboard and explain the project goal.
2. Open Class Setup or Product Center to show the teacher workflow.
3. Open Monitoring Workspace.
4. Select or confirm the active class session.
5. Start monitoring.
6. Show face recognition attendance with a trained student.
7. Show QR attendance as the backup method.
8. Show object detection with a phone and a book.
9. Explain that IoT automation can use classroom occupancy and sensor data.
10. Open Reports and show attendance or monitoring outputs.
11. Stop monitoring before ending the demo.

## Honest Demo Notes

- This is an MVP/final demo version.
- Face recognition depends on lighting, camera quality, and training data.
- QR attendance is the reliable backup for presentation.
- Object detection may run at intervals to protect camera performance.
- Public deployment needs extra security and privacy work.
