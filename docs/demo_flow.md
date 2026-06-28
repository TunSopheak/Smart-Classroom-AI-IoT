# Smart Classroom AI IoT Demo Flow

## Demo Goal

Show how the Smart Classroom platform helps teachers manage students, sessions, QR attendance, face recognition attendance, and attendance event logs.

## 1. Dashboard

Open:

http://127.0.0.1:8000/dashboard

Show:

- Total students
- Present count
- Late count
- Absent count
- Permission count
- Active session
- System status

## 2. Student Management

Open:

http://127.0.0.1:8000/dashboard/students

Show:

- Student list
- QR image
- Search/filter
- Print QR
- Print all QR
- Export CSV
- Face profile page

## 3. Face Profile

Example:

http://127.0.0.1:8000/dashboard/students/1/face-profile

Show:

- Dataset path
- Model label
- Sample count
- Trained at

## 4. Session Management

Open:

http://127.0.0.1:8000/dashboard/sessions

Show:

- Create live session
- Open session
- Close session
- Only one active session workflow

## 5. QR Attendance

Open a session attendance page.

Scan:

SC-STUDENT-S001

Show:

- Status becomes P or L
- Method becomes QR
- First seen time recorded
- Event log created

## 6. Face Recognition Attendance

Run:

python ai_module\face_recognition\recognize_face.py --session-id <SESSION_ID> --send-api --threshold 75

Show:

- Webcam recognizes S001
- API sends attendance
- Dashboard shows Method = FACE
- Confidence is stored
- Event source = opencv_webcam_recognition

## 7. Manual Override

Teacher can override:

- P
- L
- A
- Pm

Teacher can add a reason.

## Teacher Feedback Covered

The system identifies:

- Who entered the classroom
- What time they entered
- Whether the student is Present, Late, Absent, or Permission
- How attendance was recorded: QR, FACE, MANUAL, SYSTEM
- Every scan or recognition event is logged
