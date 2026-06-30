from pathlib import Path
from typing import Any

try:
    import cv2
except Exception:
    cv2 = None


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = BACKEND_ROOT / "ai_module" / "object_detection" / "models" / "yolov8n.onnx"

TARGET_LABELS = ["book", "cell phone", "person"]

EVENT_MAPPING = {
    "cell phone": "phone_usage",
    "book": "book_usage",
}


class ObjectDetectionService:
    """
    Phase 17A foundation.

    This prepares the project for real YOLO/ONNX phone/book detection.
    If the model is missing, the app must not crash.
    """

    def __init__(self):
        self.model_path = MODEL_PATH
        self.last_error = None

    def status(self) -> dict[str, Any]:
        model_exists = self.model_path.exists()
        opencv_dnn_ready = cv2 is not None and hasattr(cv2, "dnn")

        return {
            "phase": "17A-object-detection-foundation",
            "model_path": str(self.model_path),
            "model_exists": model_exists,
            "opencv_dnn_ready": opencv_dnn_ready,
            "enabled": bool(model_exists and opencv_dnn_ready),
            "target_labels": TARGET_LABELS,
            "event_mapping": EVENT_MAPPING,
            "last_error": self.last_error,
            "message": (
                "Object detection ready."
                if model_exists and opencv_dnn_ready
                else "Object detection model not installed yet. Add yolov8n.onnx to backend/ai_module/object_detection/models/."
            ),
        }

    def detect(self, frame):
        """
        Phase 17A returns no detections yet.
        Phase 17B will connect YOLO/ONNX detection to live camera frames.
        """
        return []


object_detection_service = ObjectDetectionService()
