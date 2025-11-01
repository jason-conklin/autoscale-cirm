"""Google Cloud Monitoring collector."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence

from api.collectors.base import MetricCollector, MetricSample, CollectorError

try:
    from google.cloud import monitoring_v3  # type: ignore
    from google.api_core.exceptions import GoogleAPICallError  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    monitoring_v3 = None
    GoogleAPICallError = Exception  # type: ignore


class GCPMonitoringCollector(MetricCollector):
    """Fetches metrics from Google Cloud Monitoring."""

    provider = "gcp"

    def __init__(self, project_id: str, instance_ids: Sequence[str]):
        if not monitoring_v3:
            raise CollectorError(
                "google-cloud-monitoring is not installed; cannot use GCP provider."
            )
        if not project_id:
            raise CollectorError("GCP_PROJECT_ID must be specified for GCP metrics provider.")

        self.project_id = project_id
        self.instance_ids = list(instance_ids)
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{project_id}"

    def fetch(self) -> Sequence[MetricSample]:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=10)
        samples: List[MetricSample] = []

        for instance_id in self.instance_ids:
            cpu = self._fetch_latest_value(
                metric_type="compute.googleapis.com/instance/cpu/utilization",
                instance_id=instance_id,
                start_time=start_time,
                end_time=end_time,
                scale=100.0,
            )

            mem = self._fetch_latest_value(
                metric_type="agent.googleapis.com/memory/percent_used",
                instance_id=instance_id,
                start_time=start_time,
                end_time=end_time,
                scale=1.0,
            )

            net_in = self._fetch_latest_value(
                metric_type="compute.googleapis.com/instance/network/received_bytes_count",
                instance_id=instance_id,
                start_time=start_time,
                end_time=end_time,
                scale=8.0 / 1024.0 / 60.0,
            )

            net_out = self._fetch_latest_value(
                metric_type="compute.googleapis.com/instance/network/sent_bytes_count",
                instance_id=instance_id,
                start_time=start_time,
                end_time=end_time,
                scale=8.0 / 1024.0 / 60.0,
            )

            timestamp = cpu.timestamp if cpu.value is not None else end_time

            if all(v.value is None for v in (cpu, mem, net_in, net_out)):
                continue

            samples.append(
                MetricSample(
                    provider=self.provider,
                    resource_id=instance_id,
                    timestamp=timestamp,
                    cpu_pct=cpu.value or 0.0,
                    mem_pct=mem.value or 0.0,
                    net_in_kbps=net_in.value or 0.0,
                    net_out_kbps=net_out.value or 0.0,
                )
            )

        return samples

    class _ValueWithTimestamp:
        def __init__(self, value: Optional[float], timestamp: datetime):
            self.value = value
            self.timestamp = timestamp

    def _fetch_latest_value(
        self,
        metric_type: str,
        instance_id: str,
        start_time: datetime,
        end_time: datetime,
        scale: float,
    ) -> "GCPMonitoringCollector._ValueWithTimestamp":
        interval = monitoring_v3.TimeInterval(
            {"end_time": {"seconds": int(end_time.timestamp())}, "start_time": {"seconds": int(start_time.timestamp())}}
        )
        alignment = monitoring_v3.Aggregation(
            {
                "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
                "alignment_period": {"seconds": 60},
            }
        )
        filter_str = (
            f'metric.type="{metric_type}" AND '
            f'resource.type="gce_instance" AND '
            f'resource.labels.instance_id="{instance_id}"'
        )

        request = monitoring_v3.ListTimeSeriesRequest(
            name=self.project_name,
            filter=filter_str,
            interval=interval,
            aggregation=alignment,
            view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        )

        try:
            series = list(self.client.list_time_series(request=request))
        except GoogleAPICallError as exc:  # pragma: no cover - remote call
            raise CollectorError(f"Failed to fetch {metric_type} for {instance_id}: {exc}") from exc

        if not series:
            return self._ValueWithTimestamp(None, end_time)

        points = sorted(series[0].points, key=lambda p: p.interval.end_time.seconds)
        if not points:
            return self._ValueWithTimestamp(None, end_time)

        latest = points[-1]
        ts_seconds = latest.interval.end_time.seconds
        ts_nanos = latest.interval.end_time.nanos
        ts = datetime.fromtimestamp(ts_seconds + ts_nanos / 1e9, tz=timezone.utc)
        value = latest.value.double_value if latest.value else None
        if value is not None:
            value *= scale
        return self._ValueWithTimestamp(value, ts)
