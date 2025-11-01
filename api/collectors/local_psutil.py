"""Local psutil-based metrics collector used as a fallback."""

from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

from .base import MetricCollector, MetricSample, CollectorError

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None


class LocalPsutilCollector(MetricCollector):
    """Collects metrics from the local machine using psutil."""

    provider = "local"

    def __init__(self, resource_ids: Optional[Sequence[str]] = None):
        if not psutil:
            raise CollectorError("psutil is not installed; cannot use local metrics provider.")
        self.resource_ids = list(resource_ids or ["local-node"])
        self._last_net_total = psutil.net_io_counters()
        self._last_timestamp = datetime.now(timezone.utc)

    def fetch(self) -> Sequence[MetricSample]:
        now = datetime.now(timezone.utc)
        time_delta = (now - self._last_timestamp).total_seconds() or 1.0

        cpu_pct = psutil.cpu_percent(interval=None)
        mem_pct = psutil.virtual_memory().percent

        net = psutil.net_io_counters()
        delta_bytes_in = max(0.0, net.bytes_recv - self._last_net_total.bytes_recv)
        delta_bytes_out = max(0.0, net.bytes_sent - self._last_net_total.bytes_sent)

        net_in_kbps = (delta_bytes_in * 8.0) / 1024.0 / time_delta
        net_out_kbps = (delta_bytes_out * 8.0) / 1024.0 / time_delta

        # Update state for next call.
        self._last_net_total = net
        self._last_timestamp = now

        samples: List[MetricSample] = []
        for idx, resource_id in enumerate(self.resource_ids):
            # Introduce slight variation for additional simulated resources.
            variation = math.sin(now.timestamp() / 60.0 + idx) * 5.0
            jitter = random.uniform(-2.0, 2.0)
            samples.append(
                MetricSample(
                    provider=self.provider,
                    resource_id=resource_id,
                    timestamp=now,
                    cpu_pct=max(0.0, min(100.0, cpu_pct + variation + jitter)),
                    mem_pct=max(0.0, min(100.0, mem_pct + jitter)),
                    net_in_kbps=max(0.0, net_in_kbps + random.uniform(-10.0, 10.0)),
                    net_out_kbps=max(0.0, net_out_kbps + random.uniform(-10.0, 10.0)),
                )
            )
        return samples

