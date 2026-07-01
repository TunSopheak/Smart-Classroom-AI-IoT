import time
from typing import Optional
from urllib.parse import quote

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.database import get_db, SessionLocal
from app.models.class_session import ClassSession
from app.models.student import Student
from app.services.face_product_service import (
    DATASET_DIR,
    LABELS_PATH,
    MODEL_PATH,
    capture_face_samples,
    count_student_samples,
    live_face_recognizer,
    train_lbph_model,
    upload_face_samples,
    upload_image_face_samples,
    upload_video_face_samples,
)
from app.services.face_service import FACE_ATTENDANCE_MIN_CONFIDENCE, simulate_face_attendance

router = APIRouter(tags=["Product AI Integration"])
templates = Jinja2Templates(directory="app/templates")


def get_active_or_latest_session(db: Session):
    session = (
        db.query(ClassSession)
        .filter(ClassSession.active == True)
        .order_by(ClassSession.start_time.desc())
        .first()
    )

    if session:
        return session

    return db.query(ClassSession).order_by(ClassSession.start_time.desc()).first()


def get_students(db: Session):
    return db.query(Student).filter(Student.active == True).order_by(Student.stu_id).all()


@router.get("/dashboard/product-center")
def product_center_page(request: Request, db: Session = Depends(get_db)):
    active_session = get_active_or_latest_session(db)
    students = get_students(db)

    return templates.TemplateResponse(
        request,
        "product/center.html",
        {
            "request": request,
            "active_session": active_session,
            "students": students,
            "model_exists": MODEL_PATH.exists(),
            "labels_exists": LABELS_PATH.exists(),
            "dataset_root": str(DATASET_DIR),
        },
    )


@router.get("/dashboard/qr-attendance")
def qr_attendance_page(request: Request, session_id: Optional[int] = None, db: Session = Depends(get_db)):
    sessions = db.query(ClassSession).order_by(ClassSession.start_time.desc()).limit(20).all()

    selected_session = None
    if session_id:
        selected_session = db.query(ClassSession).filter(ClassSession.id == session_id).first()

    if not selected_session:
        selected_session = get_active_or_latest_session(db)

    students = get_students(db)

    return templates.TemplateResponse(
        request,
        "attendance/qr_center.html",
        {
            "request": request,
            "sessions": sessions,
            "selected_session": selected_session,
            "students": students,
        },
    )


@router.get("/dashboard/face-training")
def face_training_page(request: Request, student_id: Optional[int] = None, db: Session = Depends(get_db)):
    students = get_students(db)

    selected_student = None
    if student_id:
        selected_student = db.query(Student).filter(Student.id == student_id).first()

    if not selected_student and students:
        selected_student = students[0]

    student_cards = []
    for student in students:
        student_cards.append(
            {
                "student": student,
                "sample_count": count_student_samples(student.stu_id),
                "dataset_path": str(DATASET_DIR / student.stu_id),
            }
        )

    return templates.TemplateResponse(
        request,
        "face_training/index.html",
        {
            "request": request,
            "students": students,
            "selected_student": selected_student,
            "student_cards": student_cards,
            "model_exists": MODEL_PATH.exists(),
            "labels_exists": LABELS_PATH.exists(),
            "model_path": str(MODEL_PATH),
            "labels_path": str(LABELS_PATH),
            "message": request.query_params.get("message"),
        },
    )


def face_training_redirect(student_id: Optional[int], message: str) -> RedirectResponse:
    selected = f"student_id={student_id}&" if student_id else ""
    return RedirectResponse(
        url=f"/dashboard/face-training?{selected}message={quote(message, safe='')}",
        status_code=303,
    )


@router.post("/dashboard/face-training/upload-images")
def face_training_upload_images(
    student_id: int = Form(...),
    images: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    result = upload_face_samples(db=db, student_id=student_id, files=images)
    return face_training_redirect(student_id, result["message"])


@router.post("/dashboard/face-training/upload-video")
def face_training_upload_video(
    student_id: int = Form(...),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    result = upload_video_face_samples(db, student_id, video)
    return face_training_redirect(student_id, result["message"])


@router.post("/dashboard/face-training/upload")
def face_training_upload_legacy(
    student_id: int = Form(...),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    result = upload_video_face_samples(db, student_id, video)
    return face_training_redirect(student_id, result["message"])


@router.post("/dashboard/face-training/capture")
def face_training_capture(
    student_id: int = Form(...),
    samples: int = Form(20),
    camera_index: int = Form(0),
    db: Session = Depends(get_db),
):
    result = capture_face_samples(
        db=db,
        student_id=student_id,
        samples=samples,
        camera_index=camera_index,
    )

    return face_training_redirect(student_id, result["message"])


@router.post("/dashboard/face-training/capture-browser")
def face_training_capture_browser(
    student_id: int = Form(...),
    images: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    result = upload_image_face_samples(db=db, student_id=student_id, files=images, source="camera")
    status_code = 200 if result["success"] else 400
    return JSONResponse(result, status_code=status_code)


@router.post("/dashboard/face-training/train")
def face_training_train(student_id: Optional[int] = Form(None), db: Session = Depends(get_db)):
    result = train_lbph_model(db)
    message = result["message"]
    if result.get("success"):
        message = (
            f"{message} Trained students: {result.get('trained_students', 0)}. "
            f"Sample count: {result.get('total_images', 0)}. Trained time: {result.get('trained_at')}."
        )
    return face_training_redirect(student_id, message)


@router.get("/dashboard/face-recognition-live")
def live_face_recognition_page(request: Request, db: Session = Depends(get_db)):
    active_session = get_active_or_latest_session(db)

    return templates.TemplateResponse(
        request,
        "face_training/live_recognition.html",
        {
            "request": request,
            "active_session": active_session,
            "model_exists": MODEL_PATH.exists(),
            "labels_exists": LABELS_PATH.exists(),
            "face_threshold": FACE_ATTENDANCE_MIN_CONFIDENCE,
        },
    )


def generate_face_recognition_stream(camera_index: int = 0):
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        frame = np.zeros((540, 960, 3), dtype=np.uint8)
        cv2.putText(frame, "Camera not available for debug face recognition.", (60, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 140, 255), 2)
        ok, buffer = cv2.imencode(".jpg", frame)
        if ok:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        return

    db = SessionLocal()
    sent_students: set[str] = set()

    try:
        while True:
            ok, frame = cap.read()

            if not ok:
                continue

            frame = cv2.resize(frame, (960, 540))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(70, 70))

            cv2.putText(
                frame,
                "Debug / Legacy Face Recognition",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.72,
                (255, 255, 255),
                2,
            )

            if len(faces) == 0:
                cv2.putText(
                    frame,
                    "No face detected",
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.70,
                (0, 255, 255),
                2,
            )

            for index, (x, y, w, h) in enumerate(faces, start=1):
                face_gray = gray[y:y + h, x:x + w]
                prediction = live_face_recognizer.predict_face(face_gray)

                if prediction and prediction["confidence"] >= FACE_ATTENDANCE_MIN_CONFIDENCE:
                    student = db.query(Student).filter(Student.stu_id == prediction["stu_id"]).first()
                    name = student.name if student else "Unknown Student"
                    attendance_text = "not recorded"
                    if student and student.stu_id not in sent_students:
                        try:
                            result = simulate_face_attendance(
                                db=db,
                                student_id=student.id,
                                session_id=None,
                                confidence=prediction["confidence"],
                                raw_source="dashboard_live_face_recognition",
                            )
                            attendance_text = result["result"]
                            sent_students.add(student.stu_id)
                        except ValueError:
                            attendance_text = "no active session"

                    label = f"{prediction['stu_id']} - {name}"
                    color = (0, 255, 0)
                elif prediction:
                    label = f"Possible {prediction['stu_id']} / low confidence {prediction['confidence']:.2f}"
                    color = (0, 140, 255)
                else:
                    label = "Unknown face"
                    color = (0, 140, 255)

                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)
                cv2.putText(
                    frame,
                    label,
                    (x, max(35, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.70,
                    color,
                    2,
                )

            ok, buffer = cv2.imencode(".jpg", frame)

            if not ok:
                continue

            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            time.sleep(0.04)

    finally:
        db.close()
        cap.release()


@router.get("/api/face-recognition-live/stream")
def face_recognition_stream(camera_index: int = 0):
    return StreamingResponse(
        generate_face_recognition_stream(camera_index=camera_index),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
