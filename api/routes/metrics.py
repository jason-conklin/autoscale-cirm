"""Metrics API routes."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import asc

from ..models import MetricRecord

metrics_bp = Blueprint("metrics", __name__, url_prefix="/api")

RANGE_TO_HOURS = {"1h": 1, "6h": 6, "24h": 24}


@metrics_bp.get("/metrics")
def list_metrics():
    """Return time-series metrics for a resource and time range."""
    session = current_app.session_factory()
    try:
        range_spec = request.args.get("range", "6h")
        range_hours = RANGE_TO_HOURS.get(range_spec, 6)
        resource_id = request.args.get("resource_id")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=range_hours)

        query = session.query(MetricRecord).filter(MetricRecord.timestamp >= start_time)
        if resource_id:
            query = query.filter(MetricRecord.resource_id == resource_id)
        else:
            # Default to the first configured resource if not specified.
            default_resource = (current_app.config.get("APP_CONFIG").resource_ids or ["local-node"])[0]
            resource_id = default_resource
            query = query.filter(MetricRecord.resource_id == resource_id)

        records = query.order_by(asc(MetricRecord.timestamp)).all()

        available_resources = [
            row[0] for row in session.query(MetricRecord.resource_id).distinct().order_by(MetricRecord.resource_id).all()
        ]
        if not available_resources:
            available_resources = current_app.config.get("APP_CONFIG").resource_ids

        data: List[Dict] = []
        for record in records:
            data.append(
                {
                    "timestamp": record.timestamp.isoformat(),
                    "cpu_pct": record.cpu_pct,
                    "mem_pct": record.mem_pct,
                    "net_in_kbps": record.net_in_kbps,
                    "net_out_kbps": record.net_out_kbps,
                }
            )

        latest_point = data[-1] if data else None

        return jsonify(
            {
                "resource_id": resource_id,
                "range": range_spec,
                "available_resources": available_resources,
                "metrics": data,
                "latest": latest_point,
            }
        )
    finally:
        session.close()

