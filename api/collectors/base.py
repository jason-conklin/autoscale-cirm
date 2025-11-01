"""Collector interfaces used by the scheduler."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Sequence


@dataclass
class MetricSample:
    """Represents a single metrics datapoint for a resource."""

    provider: str
    resource_id: str
    timestamp: datetime
    cpu_pct: float
    mem_pct: float
    net_in_kbps: float
    net_out_kbps: float


class CollectorError(RuntimeError):
    """Raised when a collector fails irrecoverably."""


class MetricCollector(ABC):
    """Interface for metric collectors."""

    provider: str = "unknown"

    @abstractmethod
    def fetch(self) -> Sequence[MetricSample]:
        """Retrieve metric samples from the upstream provider."""

