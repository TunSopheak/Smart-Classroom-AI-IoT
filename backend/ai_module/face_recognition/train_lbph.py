"""
Train OpenCV LBPH face recognizer.

Run from backend folder:

    python ai_module/face_recognition/train_lbph.py

It reads face images from:

    ai_module/face_recognition/datasets/S001/
    ai_module/face_recognition/datasets/S002/

Then saves:

    ai_module/face_recognition/models/lbph_face_model.yml
    ai_module/face_recognition/models/labels.json
"""

import json
from datetime import datetime
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def main():
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("OpenCV or NumPy is not installed.")
        print("Run: pip install -r requirements-ai.txt")
        return

    dataset_root = Path("ai_module/face_recognition/datasets")
    model_dir = Path("ai_module/face_recognition/models")
    model_dir.mkdir(parents=True, exist_ok=True)

    if not dataset_root.exists():
        print(f"Dataset folder not found: {dataset_root}")
        return

    images = []
    labels = []
    label_map = {}
    current_label = 1

    for student_folder in sorted(dataset_root.iterdir()):
        if not student_folder.is_dir():
            continue

        stu_id = student_folder.name.upper()
        image_files = [
            file for file in sorted(student_folder.iterdir())
            if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
        ]

        if not image_files:
            print(f"SKIP: {stu_id} has no images.")
            continue

        label_map[str(current_label)] = stu_id

        for image_path in image_files:
            img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)

            if img is None:
                print(f"SKIP unreadable image: {image_path}")
                continue

            img = cv2.resize(img, (200, 200))
            images.append(img)
            labels.append(current_label)

        print(f"Loaded {len(image_files)} images for {stu_id} as label {current_label}")
        current_label += 1

    if not images:
        print("No training images found. Capture face images first.")
        return

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(images, np.array(labels))

    model_path = model_dir / "lbph_face_model.yml"
    labels_path = model_dir / "labels.json"

    recognizer.save(str(model_path))

    metadata = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "total_images": len(images),
        "labels": label_map,
    }

    labels_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("Training completed successfully.")
    print(f"Total images: {len(images)}")
    print(f"Model saved: {model_path}")
    print(f"Labels saved: {labels_path}")
    print("Label map:")
    for label, stu_id in label_map.items():
        print(f"  {label} -> {stu_id}")


if __name__ == "__main__":
    main()
