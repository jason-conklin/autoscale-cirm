"""APScheduler integration for recurring data collection and forecasting."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..collectors.aws_cloudwatch import AWSCloudWatchCollector
from ..collectors.base import MetricCollector, MetricSample, CollectorError
from ..collectors.gcp_monitoring import GCPMonitoringCollector
from ..collectors.local_psutil import LocalPsutilCollector
from ..models import MetricRecord
from .config import AppConfig
from . import forecasting, alerts

LOGGER = logging.getLogger("autoscale.scheduler")


class SchedulerService:
    """Coordinates periodic metric collection, forecasting, and alerting."""

    def __init__(self, session_factory, config: AppConfig):
        self._session_factory = session_factory
        self._config = config
        self._scheduler = BackgroundScheduler()
        try:
            self._collector = self._build_collector(config)
        except CollectorError as exc:
            LOGGER.warning("Collector initialization failed (%s); falling back to local provider.", exc)
            self._collector = LocalPsutilCollector(resource_ids=config.resource_ids)
        self._job_id = "collect_metrics"

    def start(self) -> None:
        if self._scheduler.running:
            LOGGER.debug("Scheduler already running; skipping start.")
            return
        LOGGER.info("Starting scheduler with poll interval %s minutes", self._config.poll_interval_minutes)
        self._scheduler.add_job(
            func=self._run_cycle,
            trigger="interval",
            minutes=self._config.poll_interval_minutes,
            id=self._job_id,
            next_run_time=datetime.utcnow(),
            max_instances=1,
        )
        self._scheduler.start()

    def shutdown(self) -> None:
        if not self._scheduler.running:
            return
        LOGGER.info("Shutting down scheduler.")
        self._scheduler.shutdown(wait=False)

    def _run_cycle(self) -> None:
        LOGGER.debug("Running scheduler cycle for provider %s", self._config.metrics_provider)
        session: Session = self._session_factory()
        try:
            samples = self._collector.fetch()
            if samples:
                self._persist_samples(session, samples)
            forecasts = forecasting.update_forecasts(session, self._config)
            if forecasts:
                alerts.dispatch_alerts(session, forecasts, self._config)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                LOGGER.warning("Duplicate metric insertion detected; continuing.")
        except CollectorError as exc:
            session.rollback()
            LOGGER.error("Collector error: %s", exc)
        except Exception:
            session.rollback()
            LOGGER.exception("Unhandled error during scheduler cycle")
        finally:
            session.close()

    def _persist_samples(self, session: Session, samples: List[MetricSample]) -> None:
        for sample in samples:
            session.add(
                MetricRecord(
                    provider=sample.provider,
                    resource_id=sample.resource_id,
                    timestamp=sample.timestamp,
                    cpu_pct=sample.cpu_pct,
                    mem_pct=sample.mem_pct,
                    net_in_kbps=sample.net_in_kbps,
                    net_out_kbps=sample.net_out_kbps,
                )
            )
        LOGGER.debug("Persisted %d metric samples.", len(samples))

    def _build_collector(self, config: AppConfig) -> MetricCollector:
        if config.metrics_provider == "aws":
            return AWSCloudWatchCollector(region=config.aws_region or "", resource_ids=config.resource_ids)
        if config.metrics_provider == "gcp":
            return GCPMonitoringCollector(project_id=config.gcp_project_id or "", instance_ids=config.resource_ids)
        return LocalPsutilCollector(resource_ids=config.resource_ids)
