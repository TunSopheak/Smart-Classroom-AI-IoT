# Features

This document summarizes the main features available in the MVP/final demo version.

## Dashboard

- Teacher-friendly dashboard pages
- Mobile responsive layout
- Product center for quick navigation
- System health and settings pages for demo readiness

## Student Management

- Add and manage student records
- Generate QR values and QR cards
- View student details
- Connect a student record with a face profile

## Attendance

- Attendance is stored per class session
- QR attendance backup is available
- Face recognition attendance is available for trained students
- Teacher override and reports are supported in the dashboard workflow

## Face Recognition

- Uses OpenCV LBPH face recognition
- Supports local face dataset preparation
- Supports local training workflow
- Stores face data locally for the demo
- Depends on camera quality, lighting, and training data

## AI/Object Detection

- Supports person, phone, and book detection
- Used in monitoring workspace for classroom activity demo
- Detection may run at intervals to keep the camera stream responsive

## Monitoring Workspace

- Central page for the live classroom demo
- Starts and stops monitoring workflow
- Combines camera monitoring, face attendance, behavior checks, object detection, and IoT concept integration

## Reports

- Attendance report page
- AI/monitoring report support
- CSV export support for demo data

## IoT Concept

- Raspberry Pi 5 is the target demo device
- ESP32, sensors, relays, fan, and light automation are part of the project direction
- Current demo focuses on the software dashboard and local AI/attendance workflow

## Current Limitations

- This is an MVP/final demo version.
- The SQLite database is local.
- Face data and models are local.
- Public deployment needs extra security and privacy controls.
- Hardware integration may require device-specific setup during presentation.
