# Architecture

Smart Classroom with AI Monitoring uses a simple layered architecture for an MVP/final demo. The goal is to keep the system understandable, runnable on a laptop or Raspberry Pi 5, and suitable for a LAN classroom presentation.

## Layers

1. Device layer
   - Laptop webcam or Raspberry Pi camera
   - Optional ESP32 sensors
   - Optional relay modules for fan/light automation demo

2. AI layer
   - OpenCV face detection and LBPH face recognition
   - YOLO/object detection for person, phone, and book
   - Behavior and attendance services that convert AI results into dashboard events

3. Backend layer
   - FastAPI application
   - Routers for dashboard pages, attendance, reports, AI, IoT, auth, and admin tools
   - Services for business logic
   - SQLAlchemy models and CRUD helpers

4. Dashboard layer
   - Jinja2 templates
   - HTML, CSS, and JavaScript
   - Mobile responsive teacher dashboard

5. Data layer
   - SQLite local database
   - Local face datasets
   - Local trained face and object detection models
   - Local recordings and generated QR/media files

## Request Flow

Typical dashboard flow:

```text
Browser -> FastAPI route -> Service -> Database/model/media -> Jinja2 response
```

Typical AI attendance flow:

```text
Camera -> OpenCV face recognition -> Face service -> Attendance record -> Dashboard report
```

Typical QR backup flow:

```text
QR scan -> Attendance route -> Attendance service -> Attendance record -> Report
```

## Deployment Model

For the final demo, the recommended deployment model is:

```text
Laptop or Raspberry Pi 5
  -> FastAPI server
  -> SQLite database
  -> Local camera and local AI files
  -> Browser dashboard on same device or LAN device
```

The project should not be described as production cloud ready. Public deployment needs stronger authentication, HTTPS, environment secret management, file storage policy, monitoring, backups, and privacy review.
