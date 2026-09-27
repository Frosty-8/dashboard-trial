# scripts/test_pipeline.py

from pathlib import Path
import json

from app.pipeline import PPCPipeline


BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "generated"
    / "ppc_synthetic.xlsx"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "ppc_clean.parquet"
)


def main() -> None:
    print("\n" + "=" * 70)
    print("RUNNING PPC DATA INTELLIGENCE PIPELINE")
    print("=" * 70)

    pipeline = PPCPipeline()

    result = pipeline.run_and_save(
        file_path=INPUT_FILE,
        output_path=OUTPUT_FILE,
        sheet_name="PPC Report",
    )

    print("\n[1] INGESTION")
    print(
        f"Rows      : {result.raw.height:,}"
    )
    print(
        f"Columns   : {result.raw.width:,}"
    )

    print("\n[2] DATA QUALITY")
    print(
        f"Duplicates: "
        f"{result.profile['duplicate_rows']:,}"
    )
    print(
        f"Nulls     : "
        f"{result.profile['total_nulls']:,}"
    )
    print(
        f"Errors    : "
        f"{result.profile['potential_errors']:,}"
    )

    print("\n[3] TRANSFORMATION")
    print(
        f"Clean rows: "
        f"{result.cleaned.height:,}"
    )
    print(
        f"Final rows: "
        f"{result.transformed.height:,}"
    )
    print(
        f"Final cols: "
        f"{result.transformed.width:,}"
    )

    print("\n[4] KPIs")

    for key, value in result.kpis.items():
        print(
            f"{key:32} : {value}"
        )

    print("\n[5] INSIGHTS")

    print(
        f"Total insights : "
        f"{result.insights['total_insights']}"
    )

    print(
        f"Critical       : "
        f"{result.insights['critical']}"
    )

    print(
        f"Warnings       : "
        f"{result.insights['warning']}"
    )

    print(
        f"Informational  : "
        f"{result.insights['info']}"
    )

    for insight in result.insights["items"]:
        print(
            f"\n[{insight['severity'].upper()}] "
            f"{insight['title']}"
        )

        print(
            f"  {insight['description']}"
        )

    print("\n[6] UNMAPPED COLUMNS")

    if result.unmapped_columns:
        for column in result.unmapped_columns:
            print(f"  - {column}")
    else:
        print("  None")

    print("\n[7] OUTPUT")
    print(
        f"  {OUTPUT_FILE}"
    )

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()