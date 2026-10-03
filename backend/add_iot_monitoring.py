from pathlib import Path

ROOT = Path(__file__).resolve().parent

def write_file(relative_path: str, content: str):
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"Written: {path}")

write_file("app/schemas/iot_schema.py", r"""
from typing import Optional

from pydantic import BaseModel, Field


class DeviceRead(BaseModel):
    id: int
    name: str
    type: str
    location: Optional[str] = None
    status: str
    last_seen: Optional[str] = None


class SensorReadingCreate(BaseModel):
    device_id: int
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    noise_level: Optional[float] = None
    light_level: Optional[float] = None


class SensorReadingRead(BaseModel):
    id: int
    device_id: int
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    noise_level: Optional[float] = None
    light_level: Optional[float] = None
    timestamp: str


class DeviceControlRequest(BaseModel):
    status: str = Field(..., min_length=2, max_length=30)
""")

write_file("app/services/iot_service.py", r"""
from datetime import datetime
from statistics import mean

from sqlalchemy.orm import Session

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

    device.status = status.strip().lower()
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
""")

write_file("app/routers/iot_router.py", r"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schemas.iot_schema import DeviceControlRequest, SensorReadingCreate
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

    return templates.TemplateResponse(
        request,
        "iot_monitoring/index.html",
        {
            "request": request,
            "devices": devices,
            "readings": readings,
            "stats": stats,
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
""")

write_file("app/templates/iot_monitoring/index.html", r"""
{% extends "base.html" %}

{% block title %}IoT Monitoring{% endblock %}

{% block content %}
<div class="page-header">
    <div>
        <p class="eyebrow">Phase 6 IoT Monitoring</p>
        <h1>IoT Device & Sensor Monitoring</h1>
        <p>Monitor classroom devices, sensors, and automation status.</p>
    </div>
    <a class="btn btn-secondary" href="/dashboard">Back Dashboard</a>
</div>

<div class="iot-demo-note">
    <strong>Demo Purpose:</strong>
    This dashboard simulates the future Raspberry Pi 5 + ESP32 classroom IoT workflow.
    Later, real hardware will send temperature, humidity, noise, light, and motion data to these API endpoints.
</div>

<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-label">Total Devices</div>
        <div class="stat-value">{{ stats.total_devices }}</div>
    </div>
    <div class="stat-card stat-success">
        <div class="stat-label">Online / On</div>
        <div class="stat-value">{{ stats.online_count }}</div>
    </div>
    <div class="stat-card stat-warning">
        <div class="stat-label">Temperature</div>
        <div class="stat-value">
            {{ "%.1f"|format(stats.latest_temperature) if stats.latest_temperature is not none else "-" }}°C
        </div>
    </div>
    <div class="stat-card stat-warning">
        <div class="stat-label">Noise Level</div>
        <div class="stat-value">
            {{ "%.1f"|format(stats.latest_noise_level) if stats.latest_noise_level is not none else "-" }}
        </div>
    </div>
</div>

<div class="card iot-action-card">
    <div>
        <h2>Quick IoT Demo Actions</h2>
        <p class="muted">Use these buttons for demo/testing before connecting Raspberry Pi or ESP32.</p>
    </div>

    <div class="quick-ai-grid">
        <form method="post" action="/dashboard/iot-monitoring/seed-demo">
            <button class="btn btn-secondary" type="submit">Seed Demo Devices</button>
        </form>

        <form method="post" action="/dashboard/iot-monitoring/simulate-reading">
            <button class="btn btn-primary" type="submit">Simulate Sensor Reading</button>
        </form>
    </div>
</div>

<div class="card">
    <h2>Device Status & Control</h2>

    <div class="table-responsive">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Device</th>
                    <th>Type</th>
                    <th>Location</th>
                    <th>Status</th>
                    <th>Last Seen</th>
                    <th>Control</th>
                </tr>
            </thead>
            <tbody>
                {% for device in devices %}
                <tr>
                    <td><strong>{{ device.name }}</strong></td>
                    <td><span class="badge badge-ai">{{ device.type }}</span></td>
                    <td>{{ device.location or "-" }}</td>
                    <td>
                        <span class="iot-status iot-status-{{ device.status }}">
                            {{ device.status }}
                        </span>
                    </td>
                    <td>{{ device.last_seen.strftime("%Y-%m-%d %H:%M:%S") if device.last_seen else "-" }}</td>
                    <td>
                        {% if device.type in ["light", "fan"] %}
                        <form method="post" action="/dashboard/iot-monitoring/control" class="inline-form">
                            <input type="hidden" name="device_id" value="{{ device.id }}">
                            {% if device.status == "on" %}
                            <input type="hidden" name="status" value="off">
                            <button class="btn btn-danger btn-sm" type="submit">Turn Off</button>
                            {% else %}
                            <input type="hidden" name="status" value="on">
                            <button class="btn btn-primary btn-sm" type="submit">Turn On</button>
                            {% endif %}
                        </form>
                        {% else %}
                        <span class="muted">Monitor only</span>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="muted">No IoT devices yet.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<div class="card">
    <h2>Latest Sensor Readings</h2>

    <div class="table-responsive">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Device</th>
                    <th>Temperature</th>
                    <th>Humidity</th>
                    <th>Noise</th>
                    <th>Light</th>
                </tr>
            </thead>
            <tbody>
                {% for reading in readings %}
                <tr>
                    <td>{{ reading.timestamp.strftime("%Y-%m-%d %H:%M:%S") if reading.timestamp else "-" }}</td>
                    <td>{{ reading.device.name if reading.device else "Unknown Device" }}</td>
                    <td>{{ "%.1f"|format(reading.temperature) if reading.temperature is not none else "-" }}°C</td>
                    <td>{{ "%.1f"|format(reading.humidity) if reading.humidity is not none else "-" }}%</td>
                    <td>{{ "%.1f"|format(reading.noise_level) if reading.noise_level is not none else "-" }}</td>
                    <td>{{ "%.1f"|format(reading.light_level) if reading.light_level is not none else "-" }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="muted">No sensor readings yet. Click Simulate Sensor Reading.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>

<div class="card">
    <h2>Automation Foundation</h2>
    <p class="muted">
        Future rule: if no students are detected in the classroom for 5 minutes, the system can automatically turn off lights and fans.
        This phase prepares the device control and sensor reading foundation for that automation.
    </p>

    <pre class="code-block">Future hardware flow:
ESP32 / Raspberry Pi → POST /api/iot/sensor-readings → Dashboard → Automation rule → Relay control</pre>
</div>
{% endblock %}
""")

# Update app/templates/base.html navigation
base_path = ROOT / "app/templates/base.html"
base_text = base_path.read_text(encoding="utf-8")
if "/dashboard/iot-monitoring" not in base_text:
    if "/dashboard/ai-monitoring" in base_text:
        base_text = base_text.replace(
            '<a href="/dashboard/ai-monitoring">AI Monitoring</a>',
            '<a href="/dashboard/ai-monitoring">AI Monitoring</a>\n    <a href="/dashboard/iot-monitoring">IoT Monitoring</a>',
            1,
        )
    elif "</nav>" in base_text:
        base_text = base_text.replace(
            "</nav>",
            '    <a href="/dashboard/iot-monitoring">IoT Monitoring</a>\n</nav>',
            1,
        )
    base_path.write_text(base_text, encoding="utf-8")
    print("Updated: app/templates/base.html")

# Update CSS
css_path = ROOT / "app/static/css/styles.css"
css_text = css_path.read_text(encoding="utf-8")
if "Phase 6 IoT Monitoring" not in css_text:
    css_text += r"""

/* Phase 6 IoT Monitoring */
.iot-demo-note {
    background: #ecfeff;
    border: 1px solid #a5f3fc;
    color: #164e63;
    padding: 1rem 1.25rem;
    border-radius: 1rem;
    margin: 1rem 0 1.5rem;
}

.stat-success {
    border-color: #bbf7d0;
    background: #f0fdf4;
}

.iot-action-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}

.iot-status {
    display: inline-block;
    padding: 0.25rem 0.55rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: capitalize;
    border: 1px solid #e5e7eb;
    background: #f8fafc;
    color: #334155;
}

.iot-status-online,
.iot-status-on {
    background: #ecfdf5;
    border-color: #bbf7d0;
    color: #047857;
}

.iot-status-offline,
.iot-status-off {
    background: #fef2f2;
    border-color: #fecaca;
    color: #b91c1c;
}

.inline-form {
    display: inline;
}

.btn-sm {
    padding: 0.45rem 0.7rem;
    font-size: 0.85rem;
}

.code-block {
    background: #0f172a;
    color: #e2e8f0;
    padding: 1rem;
    border-radius: 0.75rem;
    overflow-x: auto;
}

@media (max-width: 768px) {
    .iot-action-card {
        flex-direction: column;
        align-items: flex-start;
    }
}
"""
    css_path.write_text(css_text, encoding="utf-8")
    print("Updated: app/static/css/styles.css")

print("")
print("DONE: Phase 6 IoT Device & Sensor Monitoring files created.")
