# app/routes/upload.py

from __future__ import annotations

from flask import Blueprint, render_template


upload_bp = Blueprint(
    "upload",
    __name__,
)


@upload_bp.get("/")
def index():
    return render_template(
        "upload.html"
    )