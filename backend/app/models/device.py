from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="offline", nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sensor_readings = relationship("SensorReading", back_populates="device", cascade="all, delete-orphan")
