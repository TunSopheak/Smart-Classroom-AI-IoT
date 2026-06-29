# Phase 10 Behavior Detection Engine

## Goal

Move behavior monitoring from manual-only buttons to automatic behavior detection.

## Current Automatic Detection

The current engine uses rule-based computer vision heuristics:

- No face for 2.5 seconds -> attention_low
- No face for 5 seconds -> leaving_seat
- Face detected but eyes not detected for 4 seconds -> sleeping

## Manual Behavior Support

Manual behavior buttons are still supported:

- phone_usage
- sleeping
- leaving_seat
- attention_low
- hand_raising

Manual events appear on the live stream/recorded video and are saved to AI Monitoring.

## Why Phone Usage Is Manual For Now

Reliable phone detection requires an object detection model such as YOLO.  
This phase prepares the product workflow and event logging system, while future versions can replace manual phone usage with YOLO detection.

## Output

Detected behavior events are saved to AI Monitoring with source:

```text
camera_auto_behavior_engine
```

## Future Upgrade

- YOLO phone detection
- MediaPipe pose estimation
- Face direction / gaze estimation
- Multi-student behavior tracking
