from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

try:
    import cv2
except Exception:
    cv2 = None

try:
    import numpy as np
except Exception:
    np = None


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = BACKEND_ROOT / "ai_module" / "object_detection" / "models" / "yolov8n.onnx"

COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush",
]

TARGET_LABELS = ["book", "cell phone", "person"]

EVENT_MAPPING = {
    "cell phone": "phone_usage",
    "book": "book_usage",
}


@dataclass
class ObjectDetection:
    label: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def event_type(self) -> str | None:
        return EVENT_MAPPING.get(self.label)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["event_type"] = self.event_type
        return data


class ObjectDetectionService:
    def __init__(self):
        self.model_path = MODEL_PATH
        self.net = None
        self.loaded = False
        self.last_error = None

    def status(self) -> dict[str, Any]:
        model_exists = self.model_path.exists()
        opencv_dnn_ready = cv2 is not None and hasattr(cv2, "dnn")
        numpy_ready = np is not None

        return {
            "phase": "17B-object-detection-camera-overlay",
            "model_path": str(self.model_path),
            "model_exists": model_exists,
            "opencv_dnn_ready": opencv_dnn_ready,
            "numpy_ready": numpy_ready,
            "model_loaded": self.loaded,
            "enabled": bool(model_exists and opencv_dnn_ready and numpy_ready),
            "target_labels": TARGET_LABELS,
            "event_mapping": EVENT_MAPPING,
            "last_error": self.last_error,
            "message": (
                "Object detection ready."
                if model_exists and opencv_dnn_ready and numpy_ready
                else "Object detection model not installed yet. Add yolov8n.onnx to backend/ai_module/object_detection/models/."
            ),
        }

    def ensure_loaded(self) -> bool:
        self.last_error = None

        if cv2 is None or np is None:
            self.last_error = "OpenCV or NumPy is not available."
            return False

        if not self.model_path.exists():
            self.last_error = "Model file missing."
            return False

        if self.net is not None and self.loaded:
            return True

        try:
            self.net = cv2.dnn.readNetFromONNX(str(self.model_path))
            self.loaded = True
            return True
        except Exception as exc:
            self.net = None
            self.loaded = False
            self.last_error = str(exc)
            return False

    def detect(self, frame, confidence_threshold: float = 0.35, nms_threshold: float = 0.45):
        if frame is None:
            return []

        if not self.ensure_loaded():
            return []

        height, width = frame.shape[:2]
        input_size = 640

        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1 / 255.0,
            size=(input_size, input_size),
            mean=(0, 0, 0),
            swapRB=True,
            crop=False,
        )

        self.net.setInput(blob)
        output = self.net.forward()

        predictions = output[0]

        if len(predictions.shape) == 2 and predictions.shape[0] < predictions.shape[1]:
            predictions = predictions.T

        boxes = []
        confidences = []
        class_ids = []

        x_scale = width / input_size
        y_scale = height / input_size

        for row in predictions:
            row = row.flatten()

            if len(row) < 6:
                continue

            # YOLOv8 ONNX: [x, y, w, h, class_scores...]
            if len(row) == 84:
                class_scores = row[4:]
                objectness = 1.0
            # YOLOv5 style: [x, y, w, h, objectness, class_scores...]
            else:
                objectness = float(row[4])
                class_scores = row[5:]

            class_id = int(np.argmax(class_scores))

            if class_id >= len(COCO_LABELS):
                continue

            label = COCO_LABELS[class_id]
            if label not in TARGET_LABELS:
                continue

            class_score = float(class_scores[class_id])
            confidence = objectness * class_score

            if confidence < confidence_threshold:
                continue

            x, y, w, h = row[:4]

            x1 = int((x - w / 2) * x_scale)
            y1 = int((y - h / 2) * y_scale)
            bw = int(w * x_scale)
            bh = int(h * y_scale)

            boxes.append([max(0, x1), max(0, y1), max(1, bw), max(1, bh)])
            confidences.append(float(confidence))
            class_ids.append(class_id)

        detections = []

        if not boxes:
            return detections

        indexes = cv2.dnn.NMSBoxes(boxes, confidences, confidence_threshold, nms_threshold)

        if indexes is None or len(indexes) == 0:
            return detections

        for idx in indexes.flatten():
            x, y, w, h = boxes[int(idx)]
            label = COCO_LABELS[class_ids[int(idx)]]

            detections.append(
                ObjectDetection(
                    label=label,
                    confidence=round(float(confidences[int(idx)]), 3),
                    x1=int(x),
                    y1=int(y),
                    x2=int(x + w),
                    y2=int(y + h),
                )
            )

        return detections


object_detection_service = ObjectDetectionService()
