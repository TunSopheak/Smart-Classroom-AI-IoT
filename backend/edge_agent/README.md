# Smart Classroom Real Edge AI Agent

This local agent runs the physical classroom camera and private AI models:

- OpenCV camera capture
- Haar face detection
- LBPH face recognition
- YOLOv8 ONNX object detection
- Stable-frame attendance decisions
- Stable, low-confidence Unknown-face gating
- Cached model hashes for lightweight heartbeats
- Secure Device Key authentication
- Edge-to-cloud inference event sync
- Local retry queue for network failures
- Semantic retry deduplication to prevent offline queue flooding
- Retry only transient connection, 408, 429, and 5xx failures
- Behavior-only events do not create duplicate attendance audits

The agent sends metadata and inference results only. It does not upload raw
camera frames, face datasets, LBPH model files, label files, or YOLO binaries.

## Local configuration

Copy `backend/.env.edge.example` to `backend/.env.edge`, then fill the Render
API URL and Device Key locally. Never commit or share `backend/.env.edge`.

## Diagnosis

From the `backend` folder:

```powershell
.\.venv\Scripts\python.exe -m edge_agent.main --diagnose --camera-test
```

## Live run

```powershell
.\.venv\Scripts\python.exe -m edge_agent.main --run
```

Press `Q` or `ESC` to stop.
