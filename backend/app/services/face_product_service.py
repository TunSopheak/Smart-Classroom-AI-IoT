import json
import uuid
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
VIDEO_DIR = FACE_ROOT / "videos"

FACE_SIZE = (200, 200)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
MIN_FACE_SIZE = 80
BLUR_VARIANCE_THRESHOLD = 60.0
JPG_QUALITY = 85
MAX_SAMPLES_PER_STUDENT = 500


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


def get_student_sample_files(stu_id: str) -> list[Path]:
    folder = DATASET_DIR / stu_id
    if not folder.exists():
        return []
    files = list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")) + list(folder.glob("*.png"))
    return sorted(files, key=lambda item: item.stat().st_mtime)


def get_student_dataset_path(stu_id: str) -> Path:
    ensure_face_dirs()
    folder = DATASET_DIR / stu_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def preprocess_face_crop(face_crop) -> np.ndarray:
    if len(face_crop.shape) == 3:
        face_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    face_crop = cv2.resize(face_crop, FACE_SIZE)
    return cv2.equalizeHist(face_crop)


def detect_best_face(image) -> tuple[int, int, int, int] | None:
    detector = get_face_detector()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(50, 50))

    if len(faces) == 0:
        return None

    return max(faces, key=lambda box: box[2] * box[3])


def save_face_crop(image, output_path: Path) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    face_box = detect_best_face(image)

    if face_box is None:
        return {"saved": False, "reason": "no_face", "message": "No face detected."}

    x, y, w, h = face_box
    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
        return {"saved": False, "reason": "too_small", "message": "Face too small, move closer."}

    face_crop = gray[y:y + h, x:x + w]
    blur_score = cv2.Laplacian(face_crop, cv2.CV_64F).var()
    if blur_score < BLUR_VARIANCE_THRESHOLD:
        return {"saved": False, "reason": "blurry", "message": "Image too blurry, try again."}

    processed = preprocess_face_crop(face_crop)
    cv2.imwrite(str(output_path), processed, [int(cv2.IMWRITE_JPEG_QUALITY), JPG_QUALITY])
    return {"saved": True, "reason": "saved", "message": "Sample saved."}


def build_skip_summary(skipped: dict[str, int]) -> str:
    messages = []
    if skipped.get("too_small"):
        messages.append(f"{skipped['too_small']} face too small, move closer.")
    if skipped.get("blurry"):
        messages.append(f"{skipped['blurry']} image too blurry, try again.")
    if skipped.get("no_face"):
        messages.append(f"{skipped['no_face']} no face detected.")
    if skipped.get("limit"):
        messages.append(f"{skipped['limit']} skipped because the student reached the {MAX_SAMPLES_PER_STUDENT} sample limit.")
    if skipped.get("invalid"):
        messages.append(f"{skipped['invalid']} invalid file(s).")
    return " ".join(messages)


def merge_skip_counts(target: dict[str, int], source: dict[str, int] | None) -> None:
    for key, value in (source or {}).items():
        target[key] = target.get(key, 0) + int(value or 0)


def augment_training_image(image: np.ndarray) -> list[np.ndarray]:
    flipped = cv2.flip(image, 1)
    brighter = cv2.convertScaleAbs(image, alpha=1.0, beta=12)
    return [image, flipped, brighter]


def upload_image_face_samples(db: Session, student_id: int, files, source: str = "image") -> dict:
    ensure_face_dirs()

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {"success": False, "message": "Student not found.", "saved": 0, "failed": 0}

    folder = get_student_dataset_path(student.stu_id)
    existing = count_student_samples(student.stu_id)
    saved = 0
    failed = 0
    skipped = {"too_small": 0, "blurry": 0, "no_face": 0, "limit": 0, "invalid": 0}

    for file in files:
        if existing + saved >= MAX_SAMPLES_PER_STUDENT:
            skipped["limit"] += 1
            failed += 1
            continue

        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in IMAGE_EXTENSIONS:
            skipped["invalid"] += 1
            failed += 1
            continue

        raw = file.file.read()
        np_array = np.frombuffer(raw, np.uint8)
        image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if image is None:
            skipped["invalid"] += 1
            failed += 1
            continue

        output = folder / f"{student.stu_id}_{source}_{existing + saved + 1:03d}.jpg"
        result = save_face_crop(image, output)
        if result["saved"]:
            saved += 1
        else:
            skipped[result["reason"]] = skipped.get(result["reason"], 0) + 1
            failed += 1

    refresh_face_profile(db, student)
    skip_summary = build_skip_summary(skipped)
    message = f"Added {saved} face sample(s) for {student.stu_id}. {failed} file(s) skipped."
    if saved:
        message += " Sample saved."
    if skip_summary:
        message += f" {skip_summary}"

    return {
        "success": saved > 0,
        "message": message,
        "saved": saved,
        "failed": failed,
        "skipped": skipped,
        "dataset_path": str(folder),
    }


def upload_face_samples(db: Session, student_id: int, files) -> dict:
    return upload_image_face_samples(db=db, student_id=student_id, files=files, source="image")


def upload_video_face_samples(db: Session, student_id: int, video_file) -> dict:
    ensure_face_dirs()

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {"success": False, "message": "Student not found.", "saved": 0}

    suffix = Path(video_file.filename or "").suffix.lower()
    if suffix not in VIDEO_EXTENSIONS:
        return {"success": False, "message": "Unsupported video type. Use MP4, AVI, MOV, or MKV.", "saved": 0}

    folder = get_student_dataset_path(student.stu_id)
    existing = count_student_samples(student.stu_id)
    if existing >= MAX_SAMPLES_PER_STUDENT:
        return {
            "success": False,
            "message": f"{student.stu_id} already has {existing} sample(s). Limit is {MAX_SAMPLES_PER_STUDENT}; remove old samples before adding more.",
            "saved": 0,
            "failed": 1,
            "skipped": {"limit": 1},
        }

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    video_file_path = VIDEO_DIR / f"{student.stu_id}_{uuid.uuid4().hex}{suffix}"

    with open(video_file_path, "wb") as f:
        f.write(video_file.file.read())

    cap = cv2.VideoCapture(str(video_file_path))

    saved = 0
    failed = 0
    skipped = {"too_small": 0, "blurry": 0, "no_face": 0, "limit": 0, "invalid": 0}
    frame_id = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_id % 3 == 0:
                if existing + saved >= MAX_SAMPLES_PER_STUDENT:
                    skipped["limit"] += 1
                    failed += 1
                    break

                output = folder / f"{student.stu_id}_video_{existing + saved + 1:03d}.jpg"
                result = save_face_crop(frame, output)
                if result["saved"]:
                    saved += 1
                else:
                    skipped[result["reason"]] = skipped.get(result["reason"], 0) + 1
                    failed += 1

            frame_id += 1
    finally:
        cap.release()
        video_file_path.unlink(missing_ok=True)

    refresh_face_profile(db, student)
    skip_summary = build_skip_summary(skipped)
    message = f"Video processed. Added {saved} face sample(s) for {student.stu_id}. {failed} frame(s) skipped."
    if skip_summary:
        message += f" {skip_summary}"

    return {
        "success": saved > 0,
        "message": message,
        "saved": saved,
        "failed": failed,
        "skipped": skipped,
        "dataset_path": str(folder),
    }


def upload_training_media_samples(db: Session, student_id: int, files) -> dict:
    total_files = len(files)
    images_processed = 0
    videos_processed = 0
    unsupported = 0
    samples_saved = 0
    skipped_count = 0
    skipped = {"too_small": 0, "blurry": 0, "no_face": 0, "limit": 0, "invalid": 0}
    messages = []

    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            images_processed += 1
            result = upload_image_face_samples(db=db, student_id=student_id, files=[file], source="image")
        elif suffix in VIDEO_EXTENSIONS:
            videos_processed += 1
            result = upload_video_face_samples(db=db, student_id=student_id, video_file=file)
        else:
            unsupported += 1
            skipped["invalid"] += 1
            skipped_count += 1
            continue

        samples_saved += int(result.get("saved") or 0)
        skipped_count += int(result.get("failed") or 0)
        merge_skip_counts(skipped, result.get("skipped"))

    if unsupported:
        messages.append(f"{unsupported} unsupported file(s) skipped.")

    skip_summary = build_skip_summary(skipped)
    if skip_summary:
        messages.append(skip_summary)

    message = (
        f"Media upload complete. Total files: {total_files}. "
        f"Images processed: {images_processed}. Videos processed: {videos_processed}. "
        f"Samples saved: {samples_saved}. Skipped: {skipped_count}."
    )
    if messages:
        message += " " + " ".join(messages)

    return {
        "success": samples_saved > 0,
        "message": message,
        "total_files": total_files,
        "images_processed": images_processed,
        "videos_processed": videos_processed,
        "samples_saved": samples_saved,
        "saved": samples_saved,
        "skipped_count": skipped_count,
        "failed": skipped_count,
        "skip_reasons": skipped,
    }

def capture_face_samples(db: Session, student_id: int, samples: int = 30, camera_index: int = 0) -> dict:
    ensure_face_dirs()

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {"success": False, "message": "Student not found.", "saved": 0}

    folder = get_student_dataset_path(student.stu_id)
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        return {
            "success": False,
            "message": f"Could not open camera index {camera_index}.",
            "saved": 0,
        }

    existing = count_student_samples(student.stu_id)
    if existing >= MAX_SAMPLES_PER_STUDENT:
        cap.release()
        return {
            "success": False,
            "message": f"{student.stu_id} already has {existing} sample(s). Limit is {MAX_SAMPLES_PER_STUDENT}; remove old samples before adding more.",
            "saved": 0,
            "failed": 1,
            "skipped": {"limit": 1},
        }

    saved = 0
    failed = 0
    skipped = {"too_small": 0, "blurry": 0, "no_face": 0, "limit": 0, "invalid": 0}
    frame_count = 0
    max_frames = max(samples * 12, 120)

    while saved < samples and frame_count < max_frames and existing + saved < MAX_SAMPLES_PER_STUDENT:
        ok, frame = cap.read()
        frame_count += 1

        if not ok:
            continue

        output = folder / f"{student.stu_id}_capture_{existing + saved + 1:03d}.jpg"
        result = save_face_crop(frame, output)
        if result["saved"]:
            saved += 1
        else:
            skipped[result["reason"]] = skipped.get(result["reason"], 0) + 1
            failed += 1

    cap.release()
    refresh_face_profile(db, student)
    skip_summary = build_skip_summary(skipped)
    message = f"Captured {saved} face sample(s) for {student.stu_id}."
    if skip_summary:
        message += f" {skip_summary}"

    return {
        "success": saved > 0,
        "message": message,
        "saved": saved,
        "failed": failed,
        "skipped": skipped,
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

            image = preprocess_face_crop(image)
            for training_image in augment_training_image(image):
                images.append(training_image)
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
        "trained_students": len(label_map),
        "trained_at": trained_at.isoformat(),
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

        face_processed = preprocess_face_crop(face_gray)
        label, distance = self.recognizer.predict(face_processed)

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
