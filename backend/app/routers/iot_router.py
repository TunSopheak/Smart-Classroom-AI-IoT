from fastapi import APIRouter

router = APIRouter(prefix="/api/iot", tags=["IoT Placeholder"])


@router.get("/status")
def iot_status() -> dict:
    return {
        "status": "placeholder",
        "message": "Raspberry Pi, ESP32, sensors, and relay automation will be implemented in Phase 6.",
        "planned_devices": ["Raspberry Pi 5", "ESP32", "DHT22", "noise_sensor", "relay", "fan", "light"],
    }
