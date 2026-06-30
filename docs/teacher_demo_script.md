# Teacher Demo Script

This script uses simple English so a Cambodian CS student can present clearly and confidently.

## Short Introduction

Good morning teacher. My name is Tun Sopheak. Today I will present my project called Smart Classroom AI Monitoring IoT.

This project helps a teacher manage class attendance, monitor student behavior, detect phone or book usage, and control classroom IoT devices from one dashboard.

## Problem Statement

In a normal classroom, the teacher spends time checking attendance manually. It is also difficult to monitor phone usage, student attention, and classroom occupancy at the same time.

For a big class, these tasks can take time and may not be accurate. So our project tries to support the teacher with AI and IoT automation.

## System Objective

The objective is to build a smart classroom system that can:

- Record attendance using FACE recognition or QR backup.
- Detect phone, book, and person objects in the camera stream.
- Monitor simple behavior events.
- Estimate classroom occupancy.
- Simulate automatic light and fan control.
- Keep recording manual for privacy.
- Provide reports for teacher review.

## Technologies Used

- FastAPI for backend API and web routes.
- Jinja2 for dashboard pages.
- SQLAlchemy and SQLite for database.
- OpenCV Haar Cascade for face detection.
- OpenCV LBPH for face recognition.
- YOLOv8 ONNX for person, phone, and book detection.
- JavaScript for live status updates.
- Simulated IoT relays for light and fan control.
- Role-based login for admin, teacher, and viewer.

## Step-By-Step Demo Speech

1. "First, I login as a teacher."
2. "This dashboard is the main control center for the Smart Classroom."
3. "In Class Setup, the teacher can manage class groups, courses, students, and enrollment."
4. "Now I open Monitoring Workspace. This is the main page for daily classroom operation."
5. "I select the active session for today's class."
6. "Now I click Start Monitoring. One button starts the shared camera pipeline."
7. "The system now runs FACE attendance, behavior checks, YOLO phone and book detection, and IoT auto control together."
8. "When I show a trained face, the system checks confidence before marking attendance."
9. "If confidence is low, the system shows unknown or low confidence, so it does not mark the wrong student."
10. "Now I show a book. The system can detect BOOK in the shared camera stream."
11. "Now I show a phone. The system can detect PHONE and update the object detection status."
12. "Phone usage can also create a behavior event after stable detection and cooldown."
13. "The IoT card shows light and fan relay status. If there is no occupancy for 5 minutes, the simulated relays turn off."
14. "Recording is manual only. This is important for privacy because the classroom should not be recorded automatically."
15. "Finally, I open Reports to show attendance and monitoring results."
16. "At the end, I click Stop Monitoring to stop the camera and monitoring services."

## Explanation Of Start Monitoring

Start Monitoring is the main one-click workflow.

When the teacher clicks it, the system starts:

- Camera stream.
- FACE attendance.
- Rule-based behavior checks.
- YOLO phone/book/person detection.
- Occupancy calculation.
- IoT auto light/fan control.

This avoids opening many separate tools. The teacher only needs one main workflow.

## Explanation Of Face Attendance

The system uses OpenCV to detect a face. Then LBPH face recognition compares the face with trained student profiles.

If the confidence is high enough, the system marks attendance for that student. If the confidence is low, the system does not mark attendance. This is safer because we do not want to mark the wrong student.

In simple words: high confidence means attendance can be marked; low confidence means use QR backup.

## Explanation Of Phone And Book Detection

The system uses YOLOv8 in ONNX format to detect objects in the shared camera stream.

The main targets are:

- Person
- Phone
- Book

YOLO does not run on every frame. It runs with interval and cache, so the video stream stays smooth. When phone or book is stable for a short time, the system can update status and log behavior events.

## Explanation Of IoT Auto Light/Fan Control

The system estimates classroom occupancy from:

- Person count from YOLO.
- Face count from camera.
- Present students from attendance.

If occupancy is detected, simulated light and fan relays stay on. If no occupancy is detected for 5 minutes, the system turns the simulated relays off.

This demonstrates the IoT idea. In a real classroom, Raspberry Pi or ESP32 can control real relay modules.

## Explanation Of Recording Privacy

Recording is not automatic. The teacher must click Start Recording manually.

This is important because camera recordings may include student faces and classroom behavior. For privacy, the system keeps recording optional and controlled by the teacher.

## Limitations

- The demo uses a laptop camera now.
- IoT relay control is simulated in software.
- Face recognition depends on lighting, camera quality, and trained samples.
- YOLO speed depends on laptop performance.
- Behavior monitoring is a rule-based prototype, not a full human activity recognition model.
- The system is designed for a final-year demo, not yet a full production school deployment.

## Future Improvements

- Connect Raspberry Pi 5 with Pi Camera for real classroom deployment.
- Connect ESP32 and relay modules for real light/fan control.
- Improve face recognition with stronger deep learning models.
- Improve behavior detection using pose estimation or action recognition.
- Add Flutter mobile app for teacher notifications.
- Add cloud backup, stronger security, and better admin analytics.

## Closing Speech

In conclusion, Smart Classroom AI Monitoring IoT combines attendance, AI monitoring, object detection, IoT automation, recording privacy, and reports in one teacher-friendly system.

The main idea is not to replace the teacher, but to help the teacher save time and monitor the classroom more effectively.

Thank you teacher for listening to my presentation.
