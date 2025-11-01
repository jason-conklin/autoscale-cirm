"""Forecast API routes."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import asc, desc

from api.models import ForecastRecord

forecast_bp = Blueprint("forecast", __name__, url_prefix="/api")


@forecast_bp.get("/forecast")
def list_forecasts():
    """Return the latest forecast data per resource."""
    session = current_app.session_factory()
    try:
        resource_id = request.args.get("resource_id")

        query = session.query(ForecastRecord)
        if resource_id:
            query = query.filter(ForecastRecord.resource_id == resource_id)

        records = query.order_by(asc(ForecastRecord.resource_id), desc(ForecastRecord.created_at)).all()
        payload = [
            {
                "resource_id": record.resource_id,
                "metric": record.metric,
                "predicted_breach_time": record.predicted_breach_time.isoformat()
                if record.predicted_breach_time
                else None,
                "confidence": record.confidence,
                "created_at": record.created_at.isoformat(),
            }
            for record in records
        ]

        return jsonify({"forecasts": payload})
    finally:
        session.close()
