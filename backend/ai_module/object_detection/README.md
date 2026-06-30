# Object Detection Models

Phase 17A prepares Smart Classroom for real phone/book detection.

Expected model path:

backend/ai_module/object_detection/models/yolov8n.onnx

Target labels:
- cell phone -> phone_usage
- book -> book_usage
- person -> occupancy / context

If the model file is missing, the app will not crash. It will show model missing status.

Next:
- Phase 17B connects YOLO/ONNX detection to camera frames.
- Phase 17C logs stable phone/book events without spam.
