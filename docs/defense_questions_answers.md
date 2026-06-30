# Defense Questions And Answers

Use these answers during project defense. Keep the answer simple, honest, and connected to the demo.

## Why use Raspberry Pi 5?

Raspberry Pi 5 is suitable for an IoT classroom because it is small, affordable, and can run Linux, Python, OpenCV, camera input, and network services. In the future, it can be placed inside the classroom to connect the camera, sensors, and relay control.

## Why use laptop camera now?

For the final demo, the laptop camera is easier and more stable. It lets us prove the software workflow first: camera stream, face attendance, YOLO detection, occupancy, and IoT logic. Later, the same idea can move to Raspberry Pi with a Pi Camera or USB camera.

## Why YOLO?

YOLO is a popular object detection model because it can detect objects in real time. It is suitable for phone, book, and person detection. In this project, YOLO runs as an ONNX model so it can be used locally without cloud dependency.

## Why LBPH face recognition?

LBPH is simple, fast, and works well for a student project demo with a small number of trained faces. It is easier to train locally than a large deep learning face model. It also works with OpenCV, which fits the project stack.

## Why QR backup?

QR backup is needed because face recognition is not perfect. Lighting, camera angle, mask, or missing training data can make recognition fail. QR gives the teacher a safe attendance method when FACE confidence is low.

## How does attendance avoid wrong marking?

The system uses confidence-gated attendance. It only marks attendance when the face match is confident enough. If confidence is low, the overlay shows unknown or low confidence, and attendance is not marked.

## What happens if confidence is low?

The system does not mark the student automatically. It shows a low-confidence message and the teacher can use QR backup. This is safer than guessing the student's name.

## How does phone detection work?

YOLO detects objects in the shared camera stream. If the model sees a phone, the overlay shows a PHONE label with confidence. The status card also updates. If phone usage stays stable for a short time, the system can log a behavior event with cooldown to avoid spam.

## How does light/fan auto-off work?

The system calculates occupancy from person count, face count, and attendance count. If occupancy is greater than zero, simulated light and fan relays stay on. If no occupancy is detected for 5 minutes, the system changes the simulated relays to off.

## Is recording automatic?

No. Recording is manual and optional for privacy. The teacher must click Start Recording. This avoids recording students without teacher control.

## What are limitations?

- Laptop camera is used for demo instead of real Raspberry Pi hardware.
- IoT light/fan relay is simulated.
- Face recognition depends on lighting and training data.
- YOLO speed depends on laptop performance.
- Behavior monitoring is a rule-based prototype.
- The system is a final demo prototype, not a production school system yet.

## What would you improve next?

Next, I would connect Raspberry Pi 5, Pi Camera, ESP32 sensors, and real relay modules. I would also improve AI accuracy with better face recognition, pose estimation for behavior, mobile notifications, cloud backup, and stronger security.
