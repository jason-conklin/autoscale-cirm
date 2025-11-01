"""Environment-driven configuration utilities for AutoScale CIRM."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load .env early so downstream modules see env vars.
load_dotenv()


@dataclass
class AlertSettings:
    """Alert output configuration."""

    slack_webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_pass: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_to: Optional[str] = None

    def channels(self) -> List[str]:
        channels: List[str] = []
        if self.slack_webhook_url:
            channels.append("slack")
        if self.smtp_host and self.smtp_to:
            channels.append("email")
        return channels


@dataclass
class AppConfig:
    """Main application configuration derived from environment variables."""

    metrics_provider: str = "local"
    poll_interval_minutes: int = 5
    threshold_cpu: float = 90.0
    threshold_mem: float = 90.0
    alert_lookahead_min: int = 60
    max_forecast_horizon_min: int = 180
    resource_ids: List[str] = field(default_factory=lambda: ["local-node"])
    aws_region: Optional[str] = None
    gcp_project_id: Optional[str] = None
    alerts: AlertSettings = field(default_factory=AlertSettings)
    database_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[1] / "autoscale.db"
    )

    def as_read_only_dict(self) -> dict:
        return {
            "provider": self.metrics_provider,
            "poll_interval_minutes": self.poll_interval_minutes,
            "threshold_cpu": self.threshold_cpu,
            "threshold_mem": self.threshold_mem,
            "alert_lookahead_min": self.alert_lookahead_min,
            "available_alert_channels": self.alerts.channels(),
            "resource_ids": self.resource_ids,
        }


def _comma_split(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def load_config() -> AppConfig:
    """Load configuration while applying sane defaults."""
    metrics_provider = os.getenv("METRICS_PROVIDER", "local").lower()
    poll_interval = int(os.getenv("POLL_INTERVAL_MINUTES", "5"))
    threshold_cpu = float(os.getenv("THRESHOLD_CPU", "90"))
    threshold_mem = float(os.getenv("THRESHOLD_MEM", "90"))
    alert_lookahead = int(os.getenv("ALERT_LOOKAHEAD_MIN", "60"))
    max_forecast_horizon = int(os.getenv("MAX_FORECAST_HORIZON_MIN", "180"))

    alerts = AlertSettings(
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=int(os.getenv("SMTP_PORT", "0")) or None,
        smtp_user=os.getenv("SMTP_USER"),
        smtp_pass=os.getenv("SMTP_PASS"),
        smtp_from=os.getenv("SMTP_FROM"),
        smtp_to=os.getenv("SMTP_TO"),
    )

    config = AppConfig(
        metrics_provider=metrics_provider,
        poll_interval_minutes=poll_interval,
        threshold_cpu=threshold_cpu,
        threshold_mem=threshold_mem,
        alert_lookahead_min=alert_lookahead,
        max_forecast_horizon_min=max_forecast_horizon,
        alerts=alerts,
    )

    if metrics_provider == "aws":
        config.aws_region = os.getenv("AWS_REGION")
        resource_ids = _comma_split(os.getenv("AWS_RESOURCE_IDS"))
        if resource_ids:
            config.resource_ids = resource_ids
    elif metrics_provider == "gcp":
        config.gcp_project_id = os.getenv("GCP_PROJECT_ID")
        resource_ids = _comma_split(os.getenv("GCP_INSTANCE_IDS"))
        if resource_ids:
            config.resource_ids = resource_ids
    else:
        resource_ids = _comma_split(os.getenv("LOCAL_RESOURCE_IDS"))
        if resource_ids:
            config.resource_ids = resource_ids

    return config


def configure_logging() -> None:
    """Set up root logging suitable for production-ish use."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

