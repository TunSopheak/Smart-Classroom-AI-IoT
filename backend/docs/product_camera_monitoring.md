# Product Camera Monitoring

## Goal

The product must support classroom video monitoring and recording inside the system.

## Features

- Live camera stream
- OpenCV face frame boxes
- Recording video into the system
- Recorded video includes frame boxes and behavior overlays
- Behavior marking during monitoring
- Recording history

## Behavior Events

Current supported behavior labels:

- phone_usage
- sleeping
- leaving_seat
- attention_low
- hand_raising

## Current Version

This phase records real video with frame boxes and manual behavior overlays.

## Next Version

The next phase will improve automatic behavior detection using CV logic and future YOLO / MediaPipe integration.
