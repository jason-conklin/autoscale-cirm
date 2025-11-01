"""Lightweight forecasting service built atop scikit-learn."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Sequence, Tuple

import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session

from ..models import ForecastRecord, MetricRecord
from .config import AppConfig

LOGGER = logging.getLogger("autoscale.forecasting")


def update_forecasts(session: Session, config: AppConfig) -> List[ForecastRecord]:
    """Train/update forecasts for each resource and metric.

    Returns the list of forecast records that were persisted in this run.
    """
    forecasts: List[ForecastRecord] = []
    horizon = timedelta(minutes=config.max_forecast_horizon_min)

    for resource_id in config.resource_ids:
        metrics = (
            session.query(MetricRecord)
            .filter(MetricRecord.resource_id == resource_id)
            .order_by(MetricRecord.timestamp.desc())
            .limit(200)
            .all()
        )
        metrics = list(reversed(metrics))
        if len(metrics) < 5:
            LOGGER.debug("Skipping forecast for %s - insufficient data points.", resource_id)
            continue

        for metric_name, threshold in (("cpu_pct", config.threshold_cpu), ("mem_pct", config.threshold_mem)):
            predicted_dt, confidence = _predict_threshold_crossing(metrics, metric_name, threshold, horizon)

            # Remove older forecasts for this resource/metric pair.
            session.query(ForecastRecord).filter(
                ForecastRecord.resource_id == resource_id, ForecastRecord.metric == metric_name
            ).delete()

            record = ForecastRecord(
                resource_id=resource_id,
                metric=metric_name,
                predicted_breach_time=predicted_dt,
                confidence=confidence,
            )
            session.add(record)
            forecasts.append(record)

    return forecasts


def _predict_threshold_crossing(
    metrics: Sequence[MetricRecord],
    metric_attr: str,
    threshold: float,
    horizon: timedelta,
) -> Tuple[Optional[datetime], Optional[float]]:
    """Use linear regression to estimate when a metric will cross a threshold."""
    times: List[float] = []
    values: List[float] = []

    start_ts = metrics[0].timestamp
    for record in metrics:
        value = getattr(record, metric_attr)
        if value is None:
            continue
        delta_minutes = (record.timestamp - start_ts).total_seconds() / 60.0
        times.append(delta_minutes)
        values.append(value)

    if len(values) < 5:
        return None, None

    X = np.array(times).reshape(-1, 1)
    y = np.array(values)

    model = LinearRegression()
    model.fit(X, y)

    slope = float(model.coef_[0])
    last_value = values[-1]
    last_time_minutes = times[-1]

    if slope <= 0.0:
        return None, None

    minutes_to_threshold = (threshold - last_value) / slope
    if minutes_to_threshold <= 0:
        predicted_dt = start_ts + timedelta(minutes=last_time_minutes)
    else:
        predicted_dt = start_ts + timedelta(minutes=last_time_minutes + minutes_to_threshold)

    # Ensure prediction lies within the configurable horizon.
    if predicted_dt - metrics[-1].timestamp > horizon:
        return None, None

    try:
        confidence = float(model.score(X, y))
    except Exception:
        confidence = None

    return predicted_dt, confidence

