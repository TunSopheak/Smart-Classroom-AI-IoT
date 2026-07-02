# Local Setup

This guide explains how to run the Smart Classroom project on a local Windows development machine.

## Requirements

- Python 3.10 or newer recommended
- Windows PowerShell
- Webcam or Raspberry Pi camera for AI demo features
- Git

## Install Dependencies

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-ai.txt
```

`requirements.txt` is for the FastAPI application. `requirements-ai.txt` is for AI and computer vision features.

## Run Backend Locally

```powershell
cd backend
$env:SMART_CLASSROOM_DEVICE_API_KEY="smart-classroom-demo-device-key"
python -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/dashboard
```

## Demo URLs

```text
http://127.0.0.1:8000/dashboard
http://127.0.0.1:8000/dashboard/monitoring-workspace
http://127.0.0.1:8000/dashboard/face-training
http://127.0.0.1:8000/dashboard/reports
```

## LAN Demo Run

Use this when another phone, tablet, or laptop should open the dashboard from the same network:

```powershell
cd backend
$env:SMART_CLASSROOM_DEVICE_API_KEY="smart-classroom-demo-device-key"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open from another device:

```text
http://<host-ip>:8000/dashboard
```

## Common Issues

- If the camera does not open, close other apps that may be using it.
- If face recognition does not mark attendance, check lighting and training data.
- If object detection is slow, wait a few seconds and hold the object clearly.
- If another device cannot connect in LAN mode, check that both devices are on the same network and the firewall allows port `8000`.

## Files Not To Commit

Do not commit local secrets or private demo data:

- `.env`
- `smart_classroom.db`
- dataset images
- trained models
- recordings
- private face data
- generated QR/media if sensitive
