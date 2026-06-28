from pathlib import Path

Path("ai_module/face_recognition/recognize_face.py").write_text(r'''"""
Run real webcam face recognition using OpenCV LBPH.

Recognition only:
    python ai_module/face_recognition/recognize_face.py

Send attendance to FastAPI:
    python ai_module/face_recognition/recognize_face.py --session-id 5 --send-api

Useful options:
    --threshold 75
    --cooldown 10
    --allow-repeat

Controls:
- Press Q to quit
"""

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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


def send_face_attendance(api_url: str, session_id: int, student_id: int, confidence: float) -> dict | None:
    payload = {
        "session_id": session_id,
        "student_id": student_id,
        "confidence": round(float(confidence), 2),
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
            return result
    except urllib.error.HTTPError as exc:
        print(f"API HTTP error: {exc.code} {exc.reason}")
    except Exception as exc:
        print(f"API send failed: {exc}")

    return None


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
    parser.add_argument("--cooldown", type=int, default=10, help="Seconds between API sends per student if --allow-repeat is used.")
    parser.add_argument("--allow-repeat", action="store_true", help="Allow repeated API sends for the same student.")
    args = parser.parse_args()

    if args.send_api and args.session_id is None:
        print("ERROR: --session-id is required when using --send-api")
        return

    model_path = Path("ai_module/face_recognition/models/lbph_face_model.yml")
    labels_path = Path("ai_module/face_recognition/models/labels.json")

    if not model_path.exists():
        print(f"Model not found: {model_path}")
        print("Run: python ai_module/face_recognition/train_lbph.py")
        return

    if not labels_path.exists():
        print(f"Labels not found: {labels_path}")
        print("Run: python ai_module/face_recognition/train_lbph.py")
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

    if args.send_api:
        if args.allow_repeat:
            print("API mode: repeat allowed with cooldown.")
        else:
            print("API mode: send once per student per recognition run.")

    sent_students: set[str] = set()
    last_sent_time: dict[str, float] = {}
    last_unknown_print = 0.0

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
            confidence = round(max(0.0, min(1.0, 1.0 - (distance / 100.0))), 2)

            if accepted and stu_id != "Unknown":
                if stu_id in sent_students and not args.allow_repeat:
                    display_text = f"{stu_id} | sent | conf={confidence:.2f}"
                    box_color = (0, 255, 255)
                else:
                    display_text = f"{stu_id} | dist={distance:.1f} | conf={confidence:.2f}"
                    box_color = (0, 255, 0)

                    if args.send_api:
                        now = time.time()
                        last_time = last_sent_time.get(stu_id, 0)

                        if args.allow_repeat or now - last_time >= args.cooldown:
                            student_id = get_student_id_by_stu_id(stu_id)

                            if student_id:
                                result = send_face_attendance(
                                    api_url=args.api_url,
                                    session_id=args.session_id,
                                    student_id=student_id,
                                    confidence=confidence,
                                )

                                if result is not None:
                                    sent_students.add(stu_id)

                                last_sent_time[stu_id] = now
                            else:
                                print(f"Student not found in database: {stu_id}")
            else:
                display_text = f"Unknown | dist={distance:.1f}"
                box_color = (0, 0, 255)

                now = time.time()
                if now - last_unknown_print >= 5:
                    print(f"Unknown face ignored. distance={distance:.1f}")
                    last_unknown_print = now

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
    if sent_students:
        print("Students sent in this run:", ", ".join(sorted(sent_students)))


if __name__ == "__main__":
    main()
''', encoding="utf-8")

print("Step 3 done: recognize_face.py cleaned for Phase 4.2.")
