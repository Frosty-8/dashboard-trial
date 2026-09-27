# scripts/run_pipeline.py

from pathlib import Path

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
    pipeline = PPCPipeline()

    result = pipeline.run_and_save(
        file_path=INPUT_FILE,
        output_path=OUTPUT_FILE,
        sheet_name="PPC Report",
    )

    print("\n" + "=" * 70)
    print("PPC DATA INTELLIGENCE PIPELINE")
    print("=" * 70)

    print("\nRAW DATA")
    print(f"Rows       : {result.raw.height:,}")
    print(f"Columns    : {result.raw.width}")

    print("\nCLEAN DATA")
    print(f"Rows       : {result.cleaned.height:,}")
    print(f"Columns    : {result.cleaned.width}")

    print("\nTRANSFORMED DATA")
    print(f"Rows       : {result.transformed.height:,}")
    print(f"Columns    : {result.transformed.width}")

    print("\nDATA QUALITY")
    print(f"Duplicates : {result.profile['duplicate_rows']:,}")
    print(f"Null values: {result.profile['total_nulls']:,}")
    print(
        f"Errors     : "
        f"{result.profile['potential_errors']:,}"
    )

    print("\nKPIs")

    for key, value in result.kpis.items():
        print(
            f"{key:30} : {value:,.2f}"
            if isinstance(value, float)
            else f"{key:30} : {value:,}"
            if isinstance(value, int)
            else f"{key:30} : {value}"
        )

    print("\nINSIGHTS")

    for insight in result.insights["items"]:
        print(
            f"[{insight['severity'].upper()}] "
            f"{insight['title']}: "
            f"{insight['description']}"
        )

    print("\nUNMAPPED COLUMNS")

    if result.unmapped_columns:
        for column in result.unmapped_columns:
            print(f"- {column}")
    else:
        print("None")

    print("\nOUTPUT")
    print(OUTPUT_FILE)

    print("=" * 70)


if __name__ == "__main__":
    main()