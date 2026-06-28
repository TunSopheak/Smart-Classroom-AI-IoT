# Phase 4 Face Recognition Prototype

This folder is prepared for OpenCV face recognition.

Folders:
- datasets/
- models/

Recommended flow:
1. Open student Face Profile page.
2. Collect face images into datasets/<stu_id>/.
3. Train OpenCV LBPH model.
4. Run face recognition.
5. Send recognized student result to FastAPI /api/attendance/face-recognize.

Install AI dependencies later:
pip install -r requirements-ai.txt

Face data is sensitive. Use volunteer/demo students only.
