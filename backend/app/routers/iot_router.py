from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schemas.iot_schema import DeviceControlRequest, SensorReadingCreate
from app.services.iot_automation_service import evaluate_auto_off_rule, list_automation_events
from app.services.iot_service import (
    create_sensor_reading,
    get_iot_stats,
    list_devices,
    list_sensor_readings,
    seed_demo_devices,
    simulate_sensor_reading,
    update_device_status,
)

router = APIRouter(tags=["IoT Monitoring"])
templates = Jinja2Templates(directory="app/templates")


def device_to_dict(device):
    return {
        "id": device.id,
        "name": device.name,
        "type": device.type,
        "location": device.location,
        "status": device.status,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
    }


def reading_to_dict(reading):
    return {
        "id": reading.id,
        "device_id": reading.device_id,
        "device_name": reading.device.name if reading.device else None,
        "temperature": reading.temperature,
        "humidity": reading.humidity,
        "noise_level": reading.noise_level,
        "light_level": reading.light_level,
        "timestamp": reading.timestamp.isoformat() if reading.timestamp else None,
    }


@router.get("/api/iot/status")
def iot_status(db: Session = Depends(get_db)) -> dict:
    stats = get_iot_stats(db)
    return {
        "status": "ok",
        "message": "IoT monitoring API is running.",
        "stats": stats,
        "planned_devices": [
            "Raspberry Pi 5",
            "ESP32",
            "DHT22",
            "noise_sensor",
            "motion_sensor",
            "relay",
            "fan",
            "light",
        ],
    }


@router.get("/api/iot/devices")
def api_list_devices(db: Session = Depends(get_db)):
    return [device_to_dict(device) for device in list_devices(db)]


@router.post("/api/iot/devices/seed-demo")
def api_seed_devices(db: Session = Depends(get_db)):
    created = seed_demo_devices(db)
    return {
        "success": True,
        "created": created,
        "message": f"{created} demo IoT devices created.",
    }


@router.post("/api/iot/devices/{device_id}/control")
def api_control_device(
    device_id: int,
    payload: DeviceControlRequest,
    db: Session = Depends(get_db),
):
    device = update_device_status(db, device_id, payload.status)
    if not device:
        return {
            "success": False,
            "message": "Device not found.",
        }

    return {
        "success": True,
        "message": f"{device.name} status updated to {device.status}.",
        "device": device_to_dict(device),
    }


@router.get("/api/iot/sensor-readings")
def api_list_sensor_readings(limit: int = 50, db: Session = Depends(get_db)):
    readings = list_sensor_readings(db, limit=limit)
    return [reading_to_dict(reading) for reading in readings]


@router.post("/api/iot/sensor-readings")
def api_create_sensor_reading(
    payload: SensorReadingCreate,
    db: Session = Depends(get_db),
):
    reading = create_sensor_reading(db, payload)
    if not reading:
        return {
            "success": False,
            "message": "Device not found.",
        }

    return {
        "success": True,
        "message": "Sensor reading saved successfully.",
        "reading": reading_to_dict(reading),
    }


@router.post("/api/iot/sensor-readings/simulate")
def api_simulate_sensor_reading(db: Session = Depends(get_db)):
    reading = simulate_sensor_reading(db)
    return {
        "success": True,
        "message": "Demo sensor reading simulated.",
        "reading": reading_to_dict(reading),
    }


@router.get("/dashboard/iot-monitoring")
def dashboard_iot_monitoring(request: Request, db: Session = Depends(get_db)):
    if not list_devices(db):
        seed_demo_devices(db)

    devices = list_devices(db)
    readings = list_sensor_readings(db, limit=50)
    stats = get_iot_stats(db)
    automation_events = list_automation_events(db, limit=30)

    return templates.TemplateResponse(
        request,
        "iot_monitoring/index.html",
        {
            "request": request,
            "devices": devices,
            "readings": readings,
            "stats": stats,
            "automation_events": automation_events,
        },
    )


@router.post("/dashboard/iot-monitoring/seed-demo")
def dashboard_seed_devices(db: Session = Depends(get_db)):
    seed_demo_devices(db)
    return RedirectResponse(url="/dashboard/iot-monitoring", status_code=303)


@router.post("/dashboard/iot-monitoring/simulate-reading")
def dashboard_simulate_sensor_reading(db: Session = Depends(get_db)):
    simulate_sensor_reading(db)
    return RedirectResponse(url="/dashboard/iot-monitoring", status_code=303)


@router.post("/dashboard/iot-monitoring/control")
def dashboard_control_device(
    device_id: int = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    update_device_status(db, device_id, status)
    return RedirectResponse(url="/dashboard/iot-monitoring", status_code=303)



@router.post("/api/iot/automation/check-auto-off")
def api_check_auto_off_rule(db: Session = Depends(get_db)):
    return evaluate_auto_off_rule(db, simulate_empty=False)


@router.post("/api/iot/automation/simulate-empty-auto-off")
def api_simulate_empty_auto_off(db: Session = Depends(get_db)):
    return evaluate_auto_off_rule(db, simulate_empty=True)


@router.post("/dashboard/iot-monitoring/check-auto-off")
def dashboard_check_auto_off_rule(db: Session = Depends(get_db)):
    evaluate_auto_off_rule(db, simulate_empty=False)
    return RedirectResponse(url="/dashboard/iot-monitoring", status_code=303)


@router.post("/dashboard/iot-monitoring/simulate-empty-auto-off")
def dashboard_simulate_empty_auto_off(db: Session = Depends(get_db)):
    evaluate_auto_off_rule(db, simulate_empty=True)
    return RedirectResponse(url="/dashboard/iot-monitoring", status_code=303)
