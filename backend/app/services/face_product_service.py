import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.models.face_profile import FaceProfile
from app.models.student import Student


BACKEND_ROOT = Path(__file__).resolve().parents[2]
FACE_ROOT = BACKEND_ROOT / "ai_module" / "face_recognition"
DATASET_DIR = FACE_ROOT / "datasets"
MODEL_DIR = FACE_ROOT / "models"
MODEL_PATH = MODEL_DIR / "lbph_face_model.yml"
LABELS_PATH = MODEL_DIR / "labels.json"

FACE_SIZE = (200, 200)


def ensure_face_dirs() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def get_face_detector():
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    return cv2.CascadeClassifier(cascade_path)


def count_student_samples(stu_id: str) -> int:
    folder = DATASET_DIR / stu_id
    if not folder.exists():
        return 0
    return len(list(folder.glob("*.jpg"))) + len(list(folder.glob("*.png"))) + len(list(folder.glob("*.jpeg")))


def get_student_dataset_path(stu_id: str) -> Path:
    ensure_face_dirs()
    folder = DATASET_DIR / stu_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_face_crop(image, output_path: Path) -> bool:
    detector = get_face_detector()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(70, 70))

    if len(faces) == 0:
        return False

    x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
    face_crop = gray[y:y + h, x:x + w]
    face_crop = cv2.resize(face_crop, FACE_SIZE)

    cv2.imwrite(str(output_path), face_crop)
    return True


def upload_face_samples(db: Session, student_id: int, files) -> dict:
    ensure_face_dirs()

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {"success": False, "message": "Student not found.", "saved": 0, "failed": 0}

    folder = get_student_dataset_path(student.stu_id)
    existing = count_student_samples(student.stu_id)

    saved = 0
    failed = 0

    for index, file in enumerate(files, start=1):
        raw = file.file.read()
        np_array = np.frombuffer(raw, np.uint8)
        image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if image is None:
            failed += 1
            continue

        output = folder / f"{student.stu_id}_upload_{existing + saved + 1:03d}.jpg"

        if save_face_crop(image, output):
            saved += 1
        else:
            failed += 1

    refresh_face_profile(db, student)

    return {
        "success": True,
        "message": f"Uploaded face samples. Saved {saved}, failed {failed}.",
        "saved": saved,
        "failed": failed,
        "dataset_path": str(folder),
    }


def capture_face_samples(db: Session, student_id: int, samples: int = 30, camera_index: int = 0) -> dict:
    ensure_face_dirs()

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {"success": False, "message": "Student not found.", "saved": 0}

    folder = get_student_dataset_path(student.stu_id)
    detector = get_face_detector()
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        return {
            "success": False,
            "message": f"Could not open camera index {camera_index}.",
            "saved": 0,
        }

    existing = count_student_samples(student.stu_id)
    saved = 0
    frame_count = 0
    max_frames = max(samples * 12, 120)

    while saved < samples and frame_count < max_frames:
        ok, frame = cap.read()
        frame_count += 1

        if not ok:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(70, 70))

        if len(faces) == 0:
            continue

        x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
        face_crop = gray[y:y + h, x:x + w]
        face_crop = cv2.resize(face_crop, FACE_SIZE)

        output = folder / f"{student.stu_id}_capture_{existing + saved + 1:03d}.jpg"
        cv2.imwrite(str(output), face_crop)
        saved += 1

    cap.release()
    refresh_face_profile(db, student)

    return {
        "success": saved > 0,
        "message": f"Captured {saved} face sample(s) for {student.stu_id}.",
        "saved": saved,
        "dataset_path": str(folder),
    }


def train_lbph_model(db: Session) -> dict:
    ensure_face_dirs()

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    images = []
    labels = []
    label_map = {}
    current_label = 1

    students = db.query(Student).filter(Student.active == True).order_by(Student.id).all()

    for student in students:
        folder = DATASET_DIR / student.stu_id
        if not folder.exists():
            continue

        files = list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")) + list(folder.glob("*.png"))
        if not files:
            continue

        label_map[current_label] = student.stu_id

        for file_path in files:
            image = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                continue

            image = cv2.resize(image, FACE_SIZE)
            images.append(image)
            labels.append(current_label)

        current_label += 1

    if not images:
        return {
            "success": False,
            "message": "No face dataset images found. Upload or capture samples first.",
            "total_images": 0,
        }

    recognizer.train(images, np.array(labels))
    recognizer.write(str(MODEL_PATH))

    trained_at = datetime.utcnow()

    labels_data = {
        "trained_at": trained_at.isoformat(),
        "total_images": len(images),
        "labels": {str(key): value for key, value in label_map.items()},
    }

    LABELS_PATH.write_text(json.dumps(labels_data, indent=2), encoding="utf-8")

    for numeric_label, stu_id in label_map.items():
        student = db.query(Student).filter(Student.stu_id == stu_id).first()
        if student:
            profile = refresh_face_profile(db, student)
            profile.model_label = numeric_label
            profile.trained_at = trained_at

    db.commit()

    return {
        "success": True,
        "message": f"Training completed with {len(images)} image(s) and {len(label_map)} student label(s).",
        "total_images": len(images),
        "labels": label_map,
        "model_path": str(MODEL_PATH),
    }


def refresh_face_profile(db: Session, student: Student) -> FaceProfile:
    folder = DATASET_DIR / student.stu_id
    sample_count = count_student_samples(student.stu_id)

    profile = db.query(FaceProfile).filter(FaceProfile.student_id == student.id).first()

    if not profile:
        profile = FaceProfile(
            student_id=student.id,
            dataset_path=str(folder),
            sample_count=sample_count,
        )
        db.add(profile)
    else:
        profile.dataset_path = str(folder)
        profile.sample_count = sample_count

    db.commit()
    db.refresh(profile)
    return profile


class LiveFaceRecognizer:
    def __init__(self):
        self.model_mtime = None
        self.labels_mtime = None
        self.recognizer = None
        self.label_map = {}

    def load_if_needed(self):
        if not MODEL_PATH.exists() or not LABELS_PATH.exists():
            self.recognizer = None
            self.label_map = {}
            return

        model_mtime = MODEL_PATH.stat().st_mtime
        labels_mtime = LABELS_PATH.stat().st_mtime

        if (
            self.recognizer is not None
            and self.model_mtime == model_mtime
            and self.labels_mtime == labels_mtime
        ):
            return

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(str(MODEL_PATH))

        labels_data = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
        label_map = {int(key): value for key, value in labels_data.get("labels", {}).items()}

        self.recognizer = recognizer
        self.label_map = label_map
        self.model_mtime = model_mtime
        self.labels_mtime = labels_mtime

    def predict_face(self, face_gray) -> Optional[dict]:
        self.load_if_needed()

        if self.recognizer is None:
            return None

        face_resized = cv2.resize(face_gray, FACE_SIZE)
        label, distance = self.recognizer.predict(face_resized)

        stu_id = self.label_map.get(label)
        if not stu_id:
            return None

        confidence = max(0.0, min(1.0, 1.0 - (float(distance) / 100.0)))

        return {
            "stu_id": stu_id,
            "distance": float(distance),
            "confidence": round(confidence, 2),
        }


live_face_recognizer = LiveFaceRecognizer()
