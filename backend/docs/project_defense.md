# Smart Classroom AI IoT - Project Defense Guide

## Project Title

Smart Classroom with AI Monitoring

## Main Idea

This project helps teachers manage classroom attendance, monitor student behavior, control IoT devices, and export reports using one web dashboard.

## Problem Statement

In a normal classroom, teachers spend time on:

- Manual attendance checking
- Monitoring student attention
- Checking classroom environment
- Managing lights and fans
- Preparing attendance reports manually

This system reduces those manual tasks by combining AI, IoT, and web technology.

## Proposed Solution

The system provides:

- QR attendance
- Face recognition attendance
- AI behavior monitoring
- IoT device and sensor monitoring
- Auto light/fan off rule
- Attendance and event reports
- CSV export

## System Modules

### 1. Student Management

Teachers can manage students and generate QR codes.

### 2. Session Management

Attendance is linked to each class session.

### 3. Attendance

The system supports:

- P = Present
- L = Late
- A = Absent
- Pm = Permission

### 4. Face Recognition

OpenCV is used to capture, train, and recognize student faces.

### 5. AI Monitoring

The system logs classroom behavior events:

- Phone usage
- Sleeping
- Leaving seat
- Hand raising
- Attention low

### 6. IoT Monitoring

The system simulates Raspberry Pi and ESP32 devices:

- Temperature
- Humidity
- Noise
- Light level
- Light relay
- Fan relay
- Camera module

### 7. Automation

If no students are detected for 5 minutes, the system can automatically turn off lights and fans.

### 8. Reports

Teachers can review and export:

- Attendance report
- AI event report
- IoT sensor report
- Automation report

## Architecture

Teacher Dashboard -> FastAPI Backend -> SQLite Database

QR Scanner -> Attendance Service -> Attendance Record + Event Log

OpenCV Camera -> Face Recognition -> FastAPI Attendance API

ESP32 / Raspberry Pi -> IoT API -> Sensor Readings + Automation Rule

## Why Attendance Is Not Stored in Student Table

Attendance changes by session. A student may be present in one session and absent in another. Therefore, attendance must be stored in a separate AttendanceRecord table linked to student and session.

## Future Improvements

- Flutter mobile app
- Real Raspberry Pi 5 deployment
- ESP32 real sensor integration
- YOLO object detection
- MediaPipe pose detection
- Real-time WebSocket dashboard
- PDF report export
