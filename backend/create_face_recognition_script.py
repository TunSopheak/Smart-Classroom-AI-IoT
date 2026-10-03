from pathlib import Path

Path("ai_module/face_recognition/recognize_face.py").write_text(r'''"""
Run real webcam face recognition using OpenCV LBPH.

Basic test:
    python ai_module/face_recognition/recognize_face.py

Send attendance to FastAPI:
    python ai_module/face_recognition/recognize_face.py --session-id 4 --send-api

Controls:
- Press Q to quit
"""

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


FACE_SIZE = (200, 200)


def load_label_map(labels_path: Path) -> dict[int, str]:
    data = json.loads(labels_path.read_text(encoding="utf-8"))
    labels = data.get("labels", data)
    return {int(label): stu_id for label, stu_id in labels.items()}


def get_student_id_by_stu_id(stu_id: str) -> int | None:
    try:
        from app.database.database import SessionLocal
        from app.models.student import Student
    except Exception as exc:
        print(f"Could not import database app modules: {exc}")
        return None

    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.stu_id == stu_id).first()
        return student.id if student else None
    finally:
        db.close()


def send_face_attendance(api_url: str, session_id: int, student_id: int, confidence: float) -> None:
    payload = {
        "session_id": session_id,
        "student_id": student_id,
        "confidence": confidence,
        "raw_source": "opencv_webcam_recognition",
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=f"{api_url.rstrip('/')}/api/attendance/face-recognize",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"API result: {result.get('result')} | {result.get('message')}")
    except urllib.error.HTTPError as exc:
        print(f"API HTTP error: {exc.code} {exc.reason}")
    except Exception as exc:
        print(f"API send failed: {exc}")


def main():
    try:
        import cv2
    except ImportError:
        print("OpenCV is not installed. Run: pip install -r requirements-ai.txt")
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--threshold", type=float, default=75.0, help="Lower distance is better. Try 60-85.")
    parser.add_argument("--send-api", action="store_true", help="Send recognized attendance to FastAPI.")
    parser.add_argument("--session-id", type=int, default=None, help="Required when --send-api is used.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--cooldown", type=int, default=8, help="Seconds between API sends per student.")
    args = parser.parse_args()

    if args.send_api and args.session_id is None:
        print("ERROR: --session-id is required when using --send-api")
        return

    model_path = Path("ai_module/face_recognition/models/lbph_face_model.yml")
    labels_path = Path("ai_module/face_recognition/models/labels.json")

    if not model_path.exists():
        print(f"Model not found: {model_path}")
        print("Run training first: python ai_module/face_recognition/train_lbph.py")
        return

    if not labels_path.exists():
        print(f"Labels not found: {labels_path}")
        print("Run training first: python ai_module/face_recognition/train_lbph.py")
        return

    label_map = load_label_map(labels_path)

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(model_path))

    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cap = cv2.VideoCapture(args.camera_index)

    if not cap.isOpened():
        print("Could not open camera.")
        print("Try: python ai_module/face_recognition/recognize_face.py --camera-index 1")
        return

    print("Recognition started.")
    print("Press Q to quit.")
    print(f"Threshold: {args.threshold}")
    print(f"Labels: {label_map}")

    last_sent_time: dict[str, float] = {}

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Could not read frame.")
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

            label, distance = recognizer.predict(face)
            stu_id = label_map.get(label, "Unknown")

            accepted = distance <= args.threshold
            confidence = max(0.0, min(1.0, 1.0 - (distance / 100.0)))

            if accepted:
                display_text = f"{stu_id} | dist={distance:.1f} | conf={confidence:.2f}"
                box_color = (0, 255, 0)

                if args.send_api:
                    now = time.time()
                    last_time = last_sent_time.get(stu_id, 0)

                    if now - last_time >= args.cooldown:
                        student_id = get_student_id_by_stu_id(stu_id)

                        if student_id:
                            send_face_attendance(
                                api_url=args.api_url,
                                session_id=args.session_id,
                                student_id=student_id,
                                confidence=confidence,
                            )
                            last_sent_time[stu_id] = now
                        else:
                            print(f"Student not found in database: {stu_id}")
            else:
                display_text = f"Unknown | dist={distance:.1f}"
                box_color = (0, 0, 255)

            cv2.rectangle(frame, (x, y), (x+w, y+h), box_color, 2)
            cv2.putText(
                frame,
                display_text,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                box_color,
                2,
            )

        cv2.imshow("Smart Classroom - Face Recognition", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Recognition stopped.")


if __name__ == "__main__":
    main()
''', encoding="utf-8")

print("Step 8 done: recognize_face.py updated.")
