from __future__ import annotations

import traceback
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
        print("\n" + "=" * 70)
        print("SAP PPC PROCESSING")
        print("=" * 70)

        print(f"Uploaded filename : {filename}")
        print(f"Extension         : {extension}")
        print(f"Destination       : {destination}")
        print(f"Destination exists: {destination.exists()}")
        print(f"Destination type  : {type(destination)}")

        pipeline = PPCPipeline()

        print("\n[1/2] Running pipeline...")

        result = pipeline.run(
            file_path=destination,
            sheet_name="PPC Report",
        )

        print("[2/2] Saving transformed dataset...")

        output_path = (
            PROCESSED_DIR / "ppc_clean.parquet"
        )

        result.transformed.write_parquet(
            output_path
        )

        print(f"Output path       : {output_path}")
        print(f"Output exists     : {output_path.exists()}")

        print("=" * 70)
        print("PROCESSING SUCCESS")
        print("=" * 70)

        return jsonify(
            {
                "success": True,
                "message": "Report processed successfully.",
                "filename": filename,
                "rows": result.transformed.height,
                "columns": result.transformed.width,
                "output": str(output_path),
                "redirect": "/",
            }
        )

    except Exception as exc:

        print("\n" + "=" * 70)
        print("PROCESSING FAILED")
        print("=" * 70)

        print(f"Exception type : {type(exc).__name__}")
        print(f"Exception      : {exc}")

        print("\nTRACEBACK:")
        traceback.print_exc()

        print("=" * 70)

        return jsonify(
            {
                "success": False,
                "error_type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        ), 500