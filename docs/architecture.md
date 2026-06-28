# Architecture Notes

The system uses a layered architecture:

1. Device layer: Raspberry Pi 5, Pi camera, ESP32, sensors, relays.
2. Communication layer: REST first, WebSocket/MQTT later.
3. AI layer: OpenCV face recognition first, MediaPipe/YOLO later.
4. Backend layer: FastAPI, SQLAlchemy, SQLite.
5. Application layer: Jinja2 dashboard first, Flutter later.
6. Data layer: SQLite, image dataset folders, logs, exports.

The current implementation focuses on backend and data layer foundation.
