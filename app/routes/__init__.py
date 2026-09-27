from app.routes.api import api_bp
from app.routes.dashboard import dashboard_api_bp, dashboard_page_bp
from app.routes.upload import upload_bp

__all__ = [
    "api_bp",
    "dashboard_api_bp",
    "dashboard_page_bp",
    "upload_bp",
]