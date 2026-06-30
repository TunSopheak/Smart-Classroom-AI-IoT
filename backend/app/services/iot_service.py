from datetime import datetime
from statistics import mean

from sqlalchemy.orm import Session

from app.core.constants import DeviceStatus
from app.models.device import Device
from app.models.sensor_reading import SensorReading
from app.schemas.iot_schema import SensorReadingCreate


DEMO_DEVICES = [
    {
        "name": "Raspberry Pi 5 Controller",
        "type": "raspberry_pi",
        "location": "Teacher Desk",
        "status": "online",
    },
    {
        "name": "ESP32 Classroom Node",
        "type": "esp32",
        "location": "Front Wall",
        "status": "online",
    },
    {
        "name": "DHT22 Temperature Humidity Sensor",
        "type": "dht22",
        "location": "Middle Classroom",
        "status": "online",
    },
    {
        "name": "Noise Sensor",
        "type": "noise_sensor",
        "location": "Ceiling",
        "status": "online",
    },
    {
        "name": "Motion Sensor",
        "type": "motion_sensor",
        "location": "Door Area",
        "status": "online",
    },
    {
        "name": "Classroom Light Relay",
        "type": "light",
        "location": "Ceiling Light",
        "status": "on",
    },
    {
        "name": "Classroom Fan Relay",
        "type": "fan",
        "location": "Ceiling Fan",
        "status": "off",
    },
    {
        "name": "Camera Module",
        "type": "camera",
        "location": "Front Camera",
        "status": "online",
    },
]


def seed_demo_devices(db: Session):
    created = 0

    for item in DEMO_DEVICES:
        existing = db.query(Device).filter(Device.name == item["name"]).first()
        if existing:
            continue

        device = Device(
            name=item["name"],
            type=item["type"],
            location=item["location"],
            status=item["status"],
            last_seen=datetime.utcnow(),
        )
        db.add(device)
        created += 1

    db.commit()
    return created


def list_devices(db: Session):
    return db.query(Device).order_by(Device.id.asc()).all()


def get_device(db: Session, device_id: int):
    return db.query(Device).filter(Device.id == device_id).first()


def update_device_status(db: Session, device_id: int, status: str):
    device = get_device(db, device_id)
    if not device:
        return None

    clean_status = status.value if isinstance(status, DeviceStatus) else str(status).strip().lower()
    valid_statuses = {item.value for item in DeviceStatus}
    if clean_status not in valid_statuses:
        raise ValueError(f"Invalid device status: {status}")

    device.status = clean_status
    device.last_seen = datetime.utcnow()
    db.commit()
    db.refresh(device)
    return device


def create_sensor_reading(db: Session, payload: SensorReadingCreate):
    device = get_device(db, payload.device_id)
    if not device:
        return None

    reading = SensorReading(
        device_id=payload.device_id,
        temperature=payload.temperature,
        humidity=payload.humidity,
        noise_level=payload.noise_level,
        light_level=payload.light_level,
        timestamp=datetime.utcnow(),
    )

    device.last_seen = datetime.utcnow()
    if device.status == "offline":
        device.status = "online"

    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


def simulate_sensor_reading(db: Session):
    device = (
        db.query(Device)
        .filter(Device.type.in_(["esp32", "dht22"]))
        .order_by(Device.id.asc())
        .first()
    )

    if not device:
        seed_demo_devices(db)
        device = (
            db.query(Device)
            .filter(Device.type.in_(["esp32", "dht22"]))
            .order_by(Device.id.asc())
            .first()
        )

    payload = SensorReadingCreate(
        device_id=device.id,
        temperature=31.5,
        humidity=68.0,
        noise_level=42.0,
        light_level=76.0,
    )
    return create_sensor_reading(db, payload)


def list_sensor_readings(db: Session, limit: int = 50):
    return (
        db.query(SensorReading)
        .order_by(SensorReading.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_iot_stats(db: Session):
    devices = list_devices(db)
    readings = list_sensor_readings(db, limit=20)

    online_count = len([d for d in devices if d.status in ["online", "on"]])
    offline_count = len([d for d in devices if d.status in ["offline", "off"]])

    latest = readings[0] if readings else None

    temperatures = [r.temperature for r in readings if r.temperature is not None]
    humidities = [r.humidity for r in readings if r.humidity is not None]
    noises = [r.noise_level for r in readings if r.noise_level is not None]
    lights = [r.light_level for r in readings if r.light_level is not None]

    return {
        "total_devices": len(devices),
        "online_count": online_count,
        "offline_count": offline_count,
        "latest_temperature": latest.temperature if latest else None,
        "latest_humidity": latest.humidity if latest else None,
        "latest_noise_level": latest.noise_level if latest else None,
        "latest_light_level": latest.light_level if latest else None,
        "avg_temperature": round(mean(temperatures), 2) if temperatures else None,
        "avg_humidity": round(mean(humidities), 2) if humidities else None,
        "avg_noise_level": round(mean(noises), 2) if noises else None,
        "avg_light_level": round(mean(lights), 2) if lights else None,
    }
