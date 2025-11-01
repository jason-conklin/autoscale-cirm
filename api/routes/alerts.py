"""Alert API routes."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import desc

from api.models import AlertRecord
from api.services import alerts as alert_service

alerts_bp = Blueprint("alerts", __name__, url_prefix="/api")


@alerts_bp.get("/alerts")
def list_alerts():
    """Return recent alerts."""
    session = current_app.session_factory()
    try:
        limit = min(int(request.args.get("limit", "50")), 200)
        records = (
            session.query(AlertRecord)
            .order_by(desc(AlertRecord.created_at))
            .limit(limit)
            .all()
        )
        payload = [record.to_dict() for record in records]
        return jsonify({"alerts": payload})
    finally:
        session.close()


@alerts_bp.post("/test-alert")
def trigger_test_alert():
    """Send a test alert across configured channels."""
    session = current_app.session_factory()
    config = current_app.config.get("APP_CONFIG")
    try:
        records, message, channels = alert_service.send_test_alert(session, config)
        return jsonify(
            {
                "status": "success",
                "message": message,
                "channels": channels,
            }
        )
    except Exception as exc:  # pragma: no cover
        session.rollback()
        current_app.logger.exception("Unexpected failure sending test alert: %s", exc)
        return jsonify({"status": "success", "message": "Test alert failed; see logs for details.", "channels": []})
    finally:
        session.close()
