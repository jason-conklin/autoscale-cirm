"""System-level routes for health and configuration introspection."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from api.services.alerts import available_alert_channels

system_bp = Blueprint("system", __name__, url_prefix="/api")


@system_bp.get("/health")
def health_check():
    return jsonify({"status": "ok"})


@system_bp.get("/config")
def read_config():
    config = current_app.config.get("APP_CONFIG")
    payload = config.as_read_only_dict()
    payload["available_alert_channels"] = available_alert_channels(config)
    return jsonify(payload)
