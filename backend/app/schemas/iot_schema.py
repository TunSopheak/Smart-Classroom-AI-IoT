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
