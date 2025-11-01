"""Alerting utilities for AutoScale CIRM."""

from __future__ import annotations

import json
import logging
import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Iterable, List, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.models import AlertRecord, ForecastRecord, MetricRecord
from api.services.config import AppConfig

LOGGER = logging.getLogger("autoscale.alerts")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def available_alert_channels(config: AppConfig) -> List[str]:
    """Compute available alert channels at runtime."""
    channels: List[str] = []
    if SLACK_WEBHOOK_URL:
        channels.append("slack")
    if config.alerts.smtp_host and config.alerts.smtp_to:
        channels.append("email")
    return channels


def dispatch_alerts(session: Session, forecasts: Iterable[ForecastRecord], config: AppConfig) -> None:
    """Send alerts for forecasts that fall within the lookahead window."""
    channels = available_alert_channels(config)
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
                _deliver_alert(channel, config, message)
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


def send_test_alert(session: Session, config: AppConfig) -> Tuple[List[AlertRecord], str, List[str]]:
    """Send a test alert through all configured channels."""
    channels = available_alert_channels(config)
    forecast_stub = ForecastRecord(
        resource_id="test-resource",
        metric="cpu_pct",
        predicted_breach_time=datetime.utcnow() + timedelta(minutes=5),
        confidence=0.5,
    )

    message = "Test alert from AutoScale CIRM."

    records: List[AlertRecord] = []
    successful_channels: List[str] = []
    failed_channels: List[str] = []
    if not channels:
        LOGGER.info("No delivery channels configured; storing test alert only.")
        record = AlertRecord(
            resource_id=forecast_stub.resource_id,
            metric=forecast_stub.metric,
            channel="none",
            status="stored",
            message=message,
        )
        session.add(record)
        records.append(record)
        session.commit()
        return records, "Stored test alert (no delivery channels configured).", successful_channels

    for channel in channels:
        status = "sent"
        try:
            _deliver_alert(channel, config, message)
            successful_channels.append(channel)
        except Exception as exc:  # pragma: no cover
            status = "failed"
            LOGGER.exception("Failed to deliver test alert via %s: %s", channel, exc)
            failed_channels.append(channel)
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
    if successful_channels:
        success_message = f"Test alert sent via: {', '.join(successful_channels)}"
    else:
        success_message = "Stored test alert; delivery failed for all channels."
    if failed_channels:
        success_message += f" (failed: {', '.join(failed_channels)})"
    return records, success_message, successful_channels


def _deliver_alert(channel: str, config: AppConfig, message: str) -> None:
    if channel == "slack":
        send_to_slack(message)
    elif channel == "email":
        _send_email_alert(config, message)
    else:
        raise ValueError(f"Unsupported alert channel: {channel}")


def send_to_slack(message: str) -> None:
    """Send a simple message to the configured Slack webhook."""
    if not SLACK_WEBHOOK_URL:
        raise ValueError("Slack webhook URL not configured.")

    payload = json.dumps({"text": message}).encode("utf-8")
    request = Request(
        SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:  # pragma: no cover - network call
            if response.status >= 400:
                raise ValueError(f"Slack webhook returned status {response.status}")
        LOGGER.info("Slack alert sent successfully.")
    except URLError as exc:  # pragma: no cover
        LOGGER.error("Slack webhook error: %s", exc)
        raise ValueError(f"Slack webhook error: {exc}") from exc


def _send_email_alert(config: AppConfig, message: str) -> None:
    if not config.alerts.smtp_host or not config.alerts.smtp_to or not config.alerts.smtp_from:
        raise ValueError("SMTP configuration incomplete.")

    email = EmailMessage()
    email["Subject"] = "AutoScale CIRM Alert"
    email["From"] = config.alerts.smtp_from
    email["To"] = config.alerts.smtp_to
    email.set_content(message)

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
