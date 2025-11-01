"""Database models for the AutoScale CIRM backend."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MetricRecord(Base):
    """Stores raw metric samples collected from providers."""

    __tablename__ = "metrics"
    __table_args__ = (UniqueConstraint("resource_id", "timestamp", name="uq_metric_resource_ts"),)

    id = Column(Integer, primary_key=True)
    provider = Column(String(32), nullable=False, index=True)
    resource_id = Column(String(128), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    cpu_pct = Column(Float, nullable=True)
    mem_pct = Column(Float, nullable=True)
    net_in_kbps = Column(Float, nullable=True)
    net_out_kbps = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "resource_id": self.resource_id,
            "timestamp": self.timestamp.isoformat(),
            "cpu_pct": self.cpu_pct,
            "mem_pct": self.mem_pct,
            "net_in_kbps": self.net_in_kbps,
            "net_out_kbps": self.net_out_kbps,
        }


class ForecastRecord(Base):
    """Represents predicted threshold breaches for a resource metric."""

    __tablename__ = "forecasts"
    __table_args__ = (
        Index("ix_forecast_resource_metric", "resource_id", "metric"),
        Index("ix_forecast_predicted_time", "predicted_breach_time"),
    )

    id = Column(Integer, primary_key=True)
    resource_id = Column(String(128), nullable=False, index=True)
    metric = Column(String(32), nullable=False)
    predicted_breach_time = Column(DateTime, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self) -> dict:
        return {
            "resource_id": self.resource_id,
            "metric": self.metric,
            "predicted_breach_time": self.predicted_breach_time.isoformat()
            if self.predicted_breach_time
            else None,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


class AlertRecord(Base):
    """Tracks alerts sent to downstream channels."""

    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alert_created_at", "created_at"),)

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resource_id = Column(String(128), nullable=False, index=True)
    metric = Column(String(32), nullable=False)
    channel = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, default="sent")
    message = Column(String(512), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "resource_id": self.resource_id,
            "metric": self.metric,
            "channel": self.channel,
            "status": self.status,
            "message": self.message,
        }

