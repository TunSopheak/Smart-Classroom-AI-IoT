from datetime import datetime
from pathlib import Path
import json

from app.database.database import SessionLocal
from app.models.student import Student
from app.models.face_profile import FaceProfile

labels_path = Path("ai_module/face_recognition/models/labels.json")
dataset_root = Path("ai_module/face_recognition/datasets")

if not labels_path.exists():
    raise SystemExit("labels.json not found. Train the model first.")

data = json.loads(labels_path.read_text(encoding="utf-8"))
trained_at = datetime.fromisoformat(data["trained_at"])
labels = data["labels"]

db = SessionLocal()

try:
    for label, stu_id in labels.items():
        student = db.query(Student).filter(Student.stu_id == stu_id).first()
        if not student:
            print(f"SKIP: student {stu_id} not found in database")
            continue

        dataset_path = str(dataset_root / stu_id).replace("\\", "/")
        sample_count = len(list((dataset_root / stu_id).glob("*.jpg")))

        profile = db.query(FaceProfile).filter(FaceProfile.student_id == student.id).first()

        if profile is None:
            profile = FaceProfile(
                student_id=student.id,
                dataset_path=dataset_path,
                model_label=int(label),
                sample_count=sample_count,
                trained_at=trained_at,
            )
            db.add(profile)
        else:
            profile.dataset_path = dataset_path
            profile.model_label = int(label)
            profile.sample_count = sample_count
            profile.trained_at = trained_at

        student.face_dataset_path = dataset_path

        print(f"Updated {stu_id}: samples={sample_count}, trained_at={trained_at}")

    db.commit()
    print("DONE: Face training metadata synced.")
finally:
    db.close()
