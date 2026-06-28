from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    noise_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    light_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    device = relationship("Device", back_populates="sensor_readings")
