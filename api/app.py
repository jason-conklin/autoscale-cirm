"""Flask application factory for AutoScale CIRM."""

from __future__ import annotations

import atexit
import os
import sys
from pathlib import Path
from typing import Any

from flask import Flask
from flask_cors import CORS
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Ensure local imports resolve when running `python app.py`.
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from models import Base  # noqa: E402
from routes.alerts import alerts_bp  # noqa: E402
from routes.forecast import forecast_bp  # noqa: E402
from routes.metrics import metrics_bp  # noqa: E402
from routes.system import system_bp  # noqa: E402
from services.config import configure_logging, load_config  # noqa: E402
from services.scheduler import SchedulerService  # noqa: E402


def create_app() -> Flask:
    """Application factory used by both CLI and WSGI servers."""
    configure_logging()
    config = load_config()

    app = Flask(__name__)
    app.config["APP_CONFIG"] = config

    CORS(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
    )

    engine = create_engine(
        f"sqlite:///{config.database_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)

    session_factory = scoped_session(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))

    app.session_factory = session_factory  # type: ignore[attr-defined]

    @app.teardown_appcontext
    def remove_session(_: Any) -> None:
        session_factory.remove()

    # Register blueprints.
    app.register_blueprint(system_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(forecast_bp)
    app.register_blueprint(alerts_bp)

    scheduler = SchedulerService(session_factory=session_factory, config=config)

    def start_scheduler_if_main_process() -> None:
        # Avoid double-start when Flask reloader spawns child processes.
        if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            return
        scheduler.start()

    start_scheduler_if_main_process()
    atexit.register(scheduler.shutdown)

    app.scheduler_service = scheduler  # type: ignore[attr-defined]
    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

