# app/__init__.py

from flask import Flask

from app.routes import (
    api_bp,
    dashboard_api_bp,
    dashboard_page_bp,
    upload_bp,
)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
    )

    app.register_blueprint(upload_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_api_bp)
    app.register_blueprint(dashboard_page_bp)

    return app