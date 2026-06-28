# Final Demo Checklist

## Before Demo

- Open PowerShell in the backend folder
- Start FastAPI server
- Open the final demo page
- Prepare camera for face recognition
- Make sure session #7 or latest session is available
- Make sure IoT demo devices exist
- Make sure report page has data

## Start Server

```powershell
cd "D:\IT\IT-RUPP\Y3\CN\Project\smart-classroom-ai-iot\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/dashboard/final-demo
```

## Demo Order

1. Final Demo page
2. Dashboard overview
3. Students and QR cards
4. Face profile
5. Sessions and attendance
6. Face recognition attendance
7. AI Monitoring
8. IoT Monitoring
9. Auto light/fan off rule
10. Reports and CSV export

## Important Demo Proof

Show these clearly:

- S001 attendance method = FACE
- Confidence is saved
- AI event is linked to S001
- IoT sensor readings are shown
- Light/fan control works
- Auto-off rule logs executed/skipped
- Reports page summarizes all data

## Backup Plan

If camera does not work during demo:

- Use existing face attendance record
- Explain the OpenCV workflow
- Show Face Profile sample count
- Show Attendance Event Log with FACE method

If QR scan is not available:

- Paste QR value manually: `SC-STUDENT-S001`

If IoT hardware is not available:

- Use simulated IoT devices and sensor readings
- Explain that the API is ready for ESP32/Raspberry Pi integration
