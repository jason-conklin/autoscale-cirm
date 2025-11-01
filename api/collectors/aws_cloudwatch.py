"""AWS CloudWatch metrics collector."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Sequence, Tuple

from .base import MetricCollector, MetricSample, CollectorError

try:
    import boto3  # type: ignore
    from botocore.exceptions import BotoCoreError, ClientError  # type: ignore
except Exception:  # pragma: no cover - boto3 optional in local mode
    boto3 = None
    BotoCoreError = ClientError = Exception  # type: ignore


class AWSCloudWatchCollector(MetricCollector):
    """Fetches EC2 metrics from CloudWatch."""

    provider = "aws"

    def __init__(self, region: str, resource_ids: Sequence[str]):
        if not boto3:
            raise CollectorError("boto3 is not installed; cannot use AWS provider.")
        if not region:
            raise CollectorError("AWS_REGION must be specified for AWS metrics provider.")

        self.region = region
        self.resource_ids = list(resource_ids)
        self.client = boto3.client("cloudwatch", region_name=region)

    def fetch(self) -> Sequence[MetricSample]:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=10)
        samples: List[MetricSample] = []

        for resource_id in self.resource_ids:
            cpu, ts_cpu = self._fetch_stat(
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                statistic="Average",
                dimension_name="InstanceId",
                resource_id=resource_id,
                start_time=start_time,
                end_time=end_time,
            )

            mem, _ = self._fetch_stat(
                namespace="CWAgent",
                metric_name="mem_used_percent",
                statistic="Average",
                dimension_name="InstanceId",
                resource_id=resource_id,
                start_time=start_time,
                end_time=end_time,
            )

            net_in_bytes, ts_in = self._fetch_stat(
                namespace="AWS/EC2",
                metric_name="NetworkIn",
                statistic="Sum",
                dimension_name="InstanceId",
                resource_id=resource_id,
                start_time=start_time,
                end_time=end_time,
            )

            net_out_bytes, ts_out = self._fetch_stat(
                namespace="AWS/EC2",
                metric_name="NetworkOut",
                statistic="Sum",
                dimension_name="InstanceId",
                resource_id=resource_id,
                start_time=start_time,
                end_time=end_time,
            )

            # Determine timestamp preference: fallback order CPU -> net_in -> net_out -> now
            ts = ts_cpu or ts_in or ts_out or end_time

            if cpu is None and mem is None and net_in_bytes is None and net_out_bytes is None:
                # Nothing returned for this resource; skip it quietly.
                continue

            # CloudWatch network metrics are bytes over the period (default 5 minutes).
            period_seconds = 300
            net_in_kbps = self._bytes_to_kilobits_per_sec(net_in_bytes, period_seconds)
            net_out_kbps = self._bytes_to_kilobits_per_sec(net_out_bytes, period_seconds)

            samples.append(
                MetricSample(
                    provider=self.provider,
                    resource_id=resource_id,
                    timestamp=ts,
                    cpu_pct=cpu if cpu is not None else 0.0,
                    mem_pct=mem if mem is not None else 0.0,
                    net_in_kbps=net_in_kbps,
                    net_out_kbps=net_out_kbps,
                )
            )

        return samples

    def _fetch_stat(
        self,
        namespace: str,
        metric_name: str,
        statistic: str,
        dimension_name: str,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Tuple[Optional[float], Optional[datetime]]:
        params = {
            "Namespace": namespace,
            "MetricName": metric_name,
            "Dimensions": [{"Name": dimension_name, "Value": resource_id}],
            "StartTime": start_time,
            "EndTime": end_time,
            "Period": 300,
            "Statistics": [statistic],
        }
        if metric_name.endswith("Utilization"):
            params["Unit"] = "Percent"

        try:
            response = self.client.get_metric_statistics(**params)
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover - remote call
            raise CollectorError(f"Failed to fetch {metric_name} for {resource_id}: {exc}") from exc

        datapoints = sorted(response.get("Datapoints", []), key=lambda d: d.get("Timestamp", start_time))
        if not datapoints:
            return None, None

        datapoint = datapoints[-1]
        value = datapoint.get(statistic)
        ts = datapoint.get("Timestamp")
        return value, ts

    @staticmethod
    def _bytes_to_kilobits_per_sec(value: Optional[float], period_seconds: int) -> float:
        if value is None:
            return 0.0
        if period_seconds <= 0:
            period_seconds = 300
        return (value * 8.0) / 1024.0 / float(period_seconds)
