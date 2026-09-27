from __future__ import annotations

from flask import Blueprint, render_template


upload_bp = Blueprint(
    "upload",
    __name__,
)


@upload_bp.get("/upload")
def upload_page():
    return render_template("upload.html")