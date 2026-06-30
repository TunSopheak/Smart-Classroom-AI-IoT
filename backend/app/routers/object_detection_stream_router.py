import time

import cv2
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.object_detection_service import object_detection_service

router = APIRouter(tags=["Object Detection Stream"])


def draw_status(frame, text, y=35):
    cv2.putText(
        frame,
        text,
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.78,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


def generate_object_detection_stream(camera_index: int = 0):
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        frame = 255 * __import__("numpy").ones((480, 854, 3), dtype="uint8")
        cv2.putText(frame, "Camera not available", (40, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        ok, buffer = cv2.imencode(".jpg", frame)
        if ok:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        return

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                continue

            frame = cv2.resize(frame, (960, 540))
            status = object_detection_service.status()

            draw_status(frame, "Smart Classroom Object Detection", 35)

            if not status["enabled"]:
                draw_status(frame, "Model missing: add yolov8n.onnx for phone/book detection", 75)
            else:
                detections = object_detection_service.detect(frame)

                if not detections:
                    draw_status(frame, "No target object detected", 75)

                for detection in detections:
                    if detection.label == "cell phone":
                        color = (0, 0, 255)
                        label = "PHONE"
                    elif detection.label == "book":
                        color = (255, 0, 0)
                        label = "BOOK"
                    else:
                        color = (0, 255, 0)
                        label = detection.label.upper()

                    cv2.rectangle(
                        frame,
                        (detection.x1, detection.y1),
                        (detection.x2, detection.y2),
                        color,
                        2,
                    )

                    text = f"{label} {detection.confidence:.2f}"
                    cv2.putText(
                        frame,
                        text,
                        (detection.x1, max(25, detection.y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        color,
                        2,
                        cv2.LINE_AA,
                    )

            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                continue

            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            time.sleep(0.05)

    finally:
        cap.release()


@router.get("/api/object-detection/stream")
def object_detection_stream(camera_index: int = 0):
    return StreamingResponse(
        generate_object_detection_stream(camera_index=camera_index),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
