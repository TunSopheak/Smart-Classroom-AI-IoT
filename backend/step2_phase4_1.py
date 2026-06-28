from pathlib import Path

Path("ai_module/face_recognition/capture_faces.py").write_text(r'''"""
Capture face images for one student using webcam.

Run from backend folder:

    python ai_module/face_recognition/capture_faces.py --student-id S001 --samples 30

Controls:
- Press Q to quit
- Make sure your face is clearly visible
"""

import argparse
from pathlib import Path


FACE_SIZE = (200, 200)


def main():
    try:
        import cv2
    except ImportError:
        print("OpenCV is not installed.")
        print("Run: pip install -r requirements-ai.txt")
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("--student-id", required=True, help="Example: S001")
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--camera-index", type=int, default=0)
    args = parser.parse_args()

    student_id = args.student_id.strip().upper()
    dataset_dir = Path("ai_module/face_recognition/datasets") / student_id
    dataset_dir.mkdir(parents=True, exist_ok=True)

    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cap = cv2.VideoCapture(args.camera_index)

    if not cap.isOpened():
        print("Could not open camera.")
        print("Try another camera index, for example:")
        print(f"python ai_module/face_recognition/capture_faces.py --student-id {student_id} --camera-index 1")
        return

    count = len(list(dataset_dir.glob("*.jpg")))

    print(f"Capturing faces for {student_id}")
    print(f"Saving to: {dataset_dir}")
    print("Press Q to quit.")

    while count < args.samples:
        ok, frame = cap.read()
        if not ok:
            print("Could not read camera frame.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(80, 80),
        )

        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]
            face = cv2.resize(face, FACE_SIZE)

            count += 1
            file_path = dataset_dir / f"{student_id}_{count:03d}.jpg"
            cv2.imwrite(str(file_path), face)

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"{student_id}: {count}/{args.samples}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

            if count >= args.samples:
                break

        cv2.imshow("Smart Classroom - Capture Face Samples", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

    print(f"Done. Total samples for {student_id}: {count}")
    print(f"Dataset folder: {dataset_dir}")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

print("Step 2 done: capture_faces.py updated.")
