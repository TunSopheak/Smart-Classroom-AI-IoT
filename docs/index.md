# Smart Classroom with AI Monitoring

Welcome to the documentation homepage for the **Smart Classroom with AI Monitoring - IoT Project**.

This GitHub Pages site is for project documentation only. The real FastAPI dashboard is not deployed on GitHub Pages. The application runs locally or on a LAN device during demo and development.

## Project Overview

Smart Classroom with AI Monitoring is an MVP/final demo version of a classroom management and monitoring system. It combines attendance workflows, AI camera monitoring, object detection, reports, and IoT concepts in one teacher-friendly dashboard.

The project is designed for student project presentation, portfolio sharing, and LAN-based classroom demonstration.

## Key Features

- FACE attendance with OpenCV LBPH face recognition
- QR attendance backup for reliable demo fallback
- AI monitoring dashboard for classroom activity
- Person, phone, and book detection support
- Attendance reports and CSV export support
- Mobile responsive dashboard for laptop, tablet, and phone demos
- Raspberry Pi 5 target device and IoT concept integration
- Local/LAN demo workflow for classroom presentation

## Tech Stack

- Backend: Python, FastAPI, Uvicorn
- Dashboard: Jinja2, HTML, CSS, JavaScript
- Database: SQLite and SQLAlchemy ORM
- AI/Computer Vision: OpenCV LBPH, Haar Cascade, YOLO/object detection
- Hardware target: Raspberry Pi 5, camera, optional ESP32/sensors/relay modules

## Final Release

Final demo release:

- [v1.0-final-demo](https://github.com/TunSopheak/Smart-Classroom-AI-IoT/releases/tag/v1.0-final-demo)

This release is the final MVP/demo checkpoint. It should not be described as a production cloud deployment.

## Demo Guide

- [Demo guide](demo-guide.md)
- [Final demo checklist](final-demo-checklist.md)
- [Feature summary](features.md)

## Setup Guide

- [Local setup](setup-local.md)
- [Architecture](architecture.md)

For the actual dashboard demo, run the FastAPI application locally or on LAN. Do not use GitHub Pages as an app host.

## Privacy and Security

- [Privacy and security notes](privacy-security.md)

Face data, trained models, recordings, generated QR/media, `.env` files, and local database files must stay private and should not be committed to GitHub.

Public production deployment would require additional security work, including HTTPS, authentication hardening, database migration, secret management, and a full privacy review.

## GitHub Repository

- [Smart Classroom AI IoT Repository](https://github.com/TunSopheak/Smart-Classroom-AI-IoT)
