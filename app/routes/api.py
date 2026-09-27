from __future__ import annotations

from pathlib import Path

from flask import Blueprint, jsonify, request

from app.config import PROCESSED_DIR, UPLOAD_DIR
from app.pipeline import PPCPipeline


api_bp = Blueprint(
    "api",
    __name__,
    url_prefix="/api",
)


@api_bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "SAP PPC Data Intelligence",
        }
    )


@api_bp.post("/process")
def process_report():

    uploaded_file = request.files.get("file")

    if uploaded_file is None:
        return jsonify(
            {
                "success": False,
                "message": "No file uploaded.",
            }
        ), 400

    if not uploaded_file.filename:
        return jsonify(
            {
                "success": False,
                "message": "Filename is missing.",
            }
        ), 400

    filename = Path(
        uploaded_file.filename
    ).name

    extension = Path(
        filename
    ).suffix.lower()

    allowed_extensions = {
        ".xlsx",
        ".xlsb",
        ".csv",
        ".parquet",
    }

    if extension not in allowed_extensions:
        return jsonify(
            {
                "success": False,
                "message": (
                    f"Unsupported file type: {extension}"
                ),
            }
        ), 400

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = UPLOAD_DIR / filename

    uploaded_file.save(destination)

    try:

        pipeline = PPCPipeline()

        # Run the complete pipeline and save
        # the canonical dataset.
        result = pipeline.run_and_save(
            destination,
            output_path=(
                PROCESSED_DIR / "ppc_clean.parquet"
            ),
            sheet_name="PPC Report",
        )

        return jsonify(
            {
                "success": True,
                "message": "Report processed successfully.",
                "redirect": "/",
            }
        )

    except Exception as exc:

        return jsonify(
            {
                "success": False,
                "message": str(exc),
            }
        ), 500