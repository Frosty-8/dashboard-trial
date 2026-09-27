# app/__init__.py

from flask import Flask

from app.config import settings
from app.routes import (
    api_bp, 
    upload_bp,
    dashboard_api_bp,
    dashboard_page_bp
)
from .pipeline import PPCPipeline, PipelineResult

__all__ = [
    "PPCPipeline",
    "PipelineResult",
]



def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
    )

    app.config["MAX_CONTENT_LENGTH"] = (
        settings.MAX_UPLOAD_SIZE_MB
        * 1024
        * 1024
    )

    app.register_blueprint(upload_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_api_bp)
    app.register_blueprint(dashboard_page_bp)

    return app