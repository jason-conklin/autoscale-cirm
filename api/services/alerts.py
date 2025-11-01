"""Alerting utilities for AutoScale CIRM."""

from __future__ import annotations

import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Iterable, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..models import AlertRecord, ForecastRecord, MetricRecord
from .config import AppConfig

LOGGER = logging.getLogger("autoscale.alerts")


def dispatch_alerts(session: Session, forecasts: Iterable[ForecastRecord], config: AppConfig) -> None:
    """Send alerts for forecasts that fall within the lookahead window."""
    channels = config.alerts.channels()
    if not channels:
        LOGGER.debug("No alert channels configured; skipping alert dispatch.")
        return

    now = datetime.utcnow()
    lookahead = timedelta(minutes=config.alert_lookahead_min)

    for forecast in forecasts:
        if not forecast.predicted_breach_time:
            continue
        time_to_breach = forecast.predicted_breach_time - now
        if time_to_breach > lookahead:
            continue

        if _has_recent_alert(session, forecast, lookahead):
            LOGGER.debug(
                "Alert already sent recently for %s/%s; skipping.", forecast.resource_id, forecast.metric
            )
            continue

        latest_metric = (
            session.query(MetricRecord)
            .filter(MetricRecord.resource_id == forecast.resource_id)
            .order_by(desc(MetricRecord.timestamp))
            .first()
        )

        current_value = getattr(latest_metric, forecast.metric, None) if latest_metric else None
        message = (
            f"Resource {forecast.resource_id} is forecasted to breach {forecast.metric.upper()} "
            f"threshold at {forecast.predicted_breach_time.isoformat()} (current={current_value or 'n/a'})."
        )

        for channel in channels:
            status = "sent"
            try:
                _deliver_alert(channel, config, message, forecast)
            except Exception as exc:  # pragma: no cover - network operations
                status = "failed"
                LOGGER.exception("Failed to deliver alert via %s: %s", channel, exc)
            finally:
                session.add(
                    AlertRecord(
                        resource_id=forecast.resource_id,
                        metric=forecast.metric,
                        channel=channel,
                        status=status,
                        message=message,
                    )
                )


def send_test_alert(session: Session, config: AppConfig) -> List[AlertRecord]:
    """Send a test alert through all configured channels."""
    channels = config.alerts.channels()
    if not channels:
        raise ValueError("No alert channels configured.")

    forecast_stub = ForecastRecord(
        resource_id="test-resource",
        metric="cpu_pct",
        predicted_breach_time=datetime.utcnow() + timedelta(minutes=5),
        confidence=0.5,
    )

    message = "Test alert from AutoScale CIRM."

    records: List[AlertRecord] = []
    for channel in channels:
        status = "sent"
        try:
            _deliver_alert(channel, config, message, forecast_stub)
        except Exception as exc:  # pragma: no cover
            status = "failed"
            LOGGER.exception("Failed to deliver test alert via %s: %s", channel, exc)
        finally:
            record = AlertRecord(
                resource_id=forecast_stub.resource_id,
                metric=forecast_stub.metric,
                channel=channel,
                status=status,
                message=message,
            )
            session.add(record)
            records.append(record)
    session.commit()
    return records


def _deliver_alert(channel: str, config: AppConfig, message: str, forecast: ForecastRecord) -> None:
    if channel == "slack":
        _send_slack_alert(config.alerts.slack_webhook_url, message, forecast)
    elif channel == "email":
        _send_email_alert(config, message, forecast)
    else:
        raise ValueError(f"Unsupported alert channel: {channel}")


def _send_slack_alert(webhook_url: Optional[str], message: str, forecast: ForecastRecord) -> None:
    if not webhook_url:
        raise ValueError("Slack webhook URL not configured.")

    payload = {
        "text": message,
        "attachments": [
            {
                "color": "#f97316",
                "fields": [
                    {"title": "Resource", "value": forecast.resource_id, "short": True},
                    {"title": "Metric", "value": forecast.metric, "short": True},
                    {
                        "title": "Predicted Breach",
                        "value": forecast.predicted_breach_time.isoformat() if forecast.predicted_breach_time else "n/a",
                        "short": False,
                    },
                ],
            }
        ],
    }

    request = Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:  # pragma: no cover - network call
            if response.status >= 400:
                raise ValueError(f"Slack webhook returned status {response.status}")
    except URLError as exc:  # pragma: no cover
        raise ValueError(f"Slack webhook error: {exc}") from exc


def _send_email_alert(config: AppConfig, message: str, forecast: ForecastRecord) -> None:
    if not config.alerts.smtp_host or not config.alerts.smtp_to or not config.alerts.smtp_from:
        raise ValueError("SMTP configuration incomplete.")

    email = EmailMessage()
    email["Subject"] = f"AutoScale: Forecasted saturation for {forecast.resource_id}"
    email["From"] = config.alerts.smtp_from
    email["To"] = config.alerts.smtp_to
    email.set_content(
        f"{message}\n\nConfidence: {forecast.confidence if forecast.confidence is not None else 'n/a'}"
    )

    smtp_port = config.alerts.smtp_port or 587

    with smtplib.SMTP(config.alerts.smtp_host, smtp_port, timeout=10) as server:  # pragma: no cover - network call
        server.starttls()
        if config.alerts.smtp_user and config.alerts.smtp_pass:
            server.login(config.alerts.smtp_user, config.alerts.smtp_pass)
        server.send_message(email)


def _has_recent_alert(session: Session, forecast: ForecastRecord, lookahead: timedelta) -> bool:
    cutoff = datetime.utcnow() - lookahead
    return (
        session.query(AlertRecord)
        .filter(
            AlertRecord.resource_id == forecast.resource_id,
            AlertRecord.metric == forecast.metric,
            AlertRecord.created_at >= cutoff,
        )
        .first()
        is not None
    )

