# scripts/generate_faker_data.py

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import polars as pl
from faker import Faker

fake = Faker("en_IN")

SEED = 42
random.seed(SEED)
Faker.seed(SEED)

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ROWS = 2_000

PROJECTS = [
    "India2.0",
    "India3.0",
    "EV-Program",
    "Commercial-Vehicle",
    "Passenger-Vehicle",
]

CATEGORIES = [
    "Engine",
    "Transmission",
    "Electrical",
    "Body",
    "Interior",
    "Chassis",
    "Cooling",
    "Fuel System",
    "Braking",
    "Suspension",
]

HPG_CLASSES = ["A", "B", "C", "D"]
PRIORITIES = ["Red", "Amber", "Green", "Gray"]
PLANTS = ["NCR", "BLR", "PUNE", "CHN", "GUR"]
FREQUENCIES = ["Daily", "Weekly", "Monthly"]
SERIES = ["P1", "P2", "P3", "N1", "N2", "B1", "B2"]
BUYERS = [
    "Buyer Alpha",
    "Buyer Beta",
    "Buyer Gamma",
    "Buyer Delta",
    "Buyer Epsilon",
]
COMMODITIES = [
    "Plastics",
    "Metals",
    "Electronics",
    "Rubber",
    "Forging",
    "Casting",
    "Machining",
    "Fasteners",
]

SUPPLIERS = [
    {
        "code": f"{4000 + i}",
        "name": f"{fake.company().upper().replace(' ', '')} PRIVATE LIMITED",
    }
    for i in range(1, 81)
]


def clamp(value: float, minimum: float = 0) -> float:
    return round(max(value, minimum), 2)


def generate_part_number(index: int) -> str:
    return f"{random.choice(['04C', '06A', '08K', '12B', '15D'])}-{random.randint(100, 999)}-{random.randint(100, 999)}-{random.choice(['P', 'A', 'B', 'C'])}"


def generate_description(category: str) -> str:
    descriptions = {
        "Engine": ["INTAKE MANIFOLD", "ENGINE MOUNT", "OIL FILTER HOUSING"],
        "Transmission": ["GEAR HOUSING", "CLUTCH PLATE", "TRANSMISSION COVER"],
        "Electrical": ["WIRING HARNESS", "CONTROL MODULE", "SENSOR ASSEMBLY"],
        "Body": ["DOOR PANEL", "BODY BRACKET", "BONNET ASSEMBLY"],
        "Interior": ["DASHBOARD PANEL", "SEAT BRACKET", "CONSOLE COVER"],
        "Chassis": ["CHASSIS BRACKET", "CROSS MEMBER", "FRAME SUPPORT"],
        "Cooling": ["RADIATOR PIPE", "COOLING FAN", "WATER PUMP"],
        "Fuel System": ["FUEL PIPE", "FUEL RAIL", "FUEL FILTER"],
        "Braking": ["BRAKE CALIPER", "BRAKE PAD", "BRAKE BRACKET"],
        "Suspension": ["SHOCK ABSORBER", "CONTROL ARM", "SUSPENSION BRACKET"],
    }

    return random.choice(descriptions[category])


def generate_scenario() -> str:
    return random.choices(
        [
            "healthy",
            "low_coverage",
            "critical",
            "excess",
            "in_transit",
            "demand_spike",
            "zero_demand",
        ],
        weights=[45, 18, 10, 8, 7, 7, 5],
        k=1,
    )[0]


def generate_row(index: int) -> dict:
    category = random.choice(CATEGORIES)
    supplier = random.choice(SUPPLIERS)
    scenario = generate_scenario()

    monthly_requirement = random.randint(20, 2_500)
    unit_price = round(random.uniform(40, 12_000), 2)

    if scenario == "zero_demand":
        monthly_requirement = 0
        current_stock = random.randint(0, 300)

    elif scenario == "critical":
        current_stock = random.randint(
            0,
            max(1, int(monthly_requirement * random.uniform(0.05, 0.5))),
        )

    elif scenario == "low_coverage":
        current_stock = random.randint(
            max(1, int(monthly_requirement * 0.5)),
            max(1, int(monthly_requirement * 1.5)),
        )

    elif scenario == "excess":
        current_stock = int(
            monthly_requirement * random.uniform(6, 15)
        )

    elif scenario == "demand_spike":
        monthly_requirement = int(monthly_requirement * random.uniform(1.5, 3))
        current_stock = random.randint(
            max(1, int(monthly_requirement * 0.2)),
            max(1, int(monthly_requirement * 0.8)),
        )

    else:
        current_stock = int(
            monthly_requirement * random.uniform(1.5, 5)
        )

    expected_backorder = (
        random.randint(0, max(1, int(monthly_requirement * 0.8)))
        if scenario in {"critical", "low_coverage", "demand_spike"}
        else random.randint(0, max(1, int(monthly_requirement * 0.15)))
    )

    shortfall = max(
        monthly_requirement - current_stock - expected_backorder,
        0,
    )

    coverage = (
        round(current_stock / monthly_requirement, 2)
        if monthly_requirement > 0
        else None
    )

    if monthly_requirement == 0:
        priority = "Gray"
    elif coverage < 1:
        priority = "Red"
    elif coverage < 2:
        priority = "Amber"
    elif coverage > 8:
        priority = "Gray"
    else:
        priority = "Green"

    annual_forecast = monthly_requirement * random.uniform(10, 14)

    open_po = (
        random.randint(1, 8)
        if scenario in {"critical", "low_coverage", "demand_spike"}
        else random.randint(0, 4)
    )

    sto_intransit = (
        random.randint(1, 300)
        if scenario == "in_transit"
        else random.randint(0, 100)
    )

    open_sto = (
        random.randint(1, 8)
        if scenario in {"critical", "low_coverage", "in_transit"}
        else random.randint(0, 3)
    )

    ncr_stock = int(current_stock * random.uniform(0.35, 0.65))
    blr_stock = int(current_stock * random.uniform(0.15, 0.40))

    total_mard = ncr_stock + blr_stock
    total_vbbe = sto_intransit

    actual_stock = max(total_mard - total_vbbe, 0)

    inventory_value = round(actual_stock * unit_price, 2)
    fums_value = round(current_stock * unit_price * random.uniform(0.85, 1.15), 2)

    pan_india_coverage = (
        round(actual_stock / monthly_requirement, 2)
        if monthly_requirement > 0
        else None
    )

    monthly_forecasts: dict[str, float | None] = {}
    monthly_stocks: dict[str, float | None] = {}
    monthly_coverages: dict[str, float | None] = {}

    base_date = date.today().replace(day=1)

    for month_offset in range(6):
        month_date = (
            base_date
            + timedelta(days=32 * month_offset)
        ).replace(day=1)

        month_name = month_date.strftime("%b")

        demand_multiplier = random.uniform(0.85, 1.20)

        if scenario == "demand_spike" and month_offset >= 1:
            demand_multiplier *= random.uniform(1.15, 1.60)

        forecast = (
            round(monthly_requirement * demand_multiplier, 2)
            if monthly_requirement > 0
            else 0
        )

        depletion = forecast * random.uniform(0.75, 1.0)

        if month_offset == 0:
            ending_stock = current_stock
        else:
            previous_stock = monthly_stocks[
                list(monthly_stocks.keys())[-1]
            ] or 0

            ending_stock = max(
                previous_stock - depletion + random.randint(0, 150),
                0,
            )

        ending_coverage = (
            round(ending_stock / forecast, 2)
            if forecast > 0
            else None
        )

        monthly_forecasts[f"{month_name}_forecast"] = forecast
        monthly_stocks[f"{month_name}_end_stock"] = round(
            ending_stock,
            2,
        )
        monthly_coverages[f"{month_name}_end_coverage"] = (
            ending_coverage
        )

    row = {
        "project": random.choice(PROJECTS),
        "part_no": generate_part_number(index),
        "description": generate_description(category),
        "vendor_code": supplier["code"],
        "new_vendor_code": supplier["code"],
        "supplier": supplier["name"],
        "monthly_requirement": monthly_requirement,
        "stock_as_on_date": current_stock,
        "expected_backorder": expected_backorder,
        "shortfall_quantity": shortfall,
        "coverage": coverage,
        "priority": priority,
        "annual_sales_forecast": round(annual_forecast, 2),
        "ncr_stock": ncr_stock,
        "blr_stock": blr_stock,
        "open_po": open_po,
        "open_sto": open_sto,
        "sto_intransit": sto_intransit,
        "category": category,
        "vol": round(random.uniform(0.1, 25), 2),
        "hpg_class": random.choice(HPG_CLASSES),
        "series": random.choice(SERIES),
        "series_buyer": random.choice(BUYERS),
        "commodity_head": random.choice(COMMODITIES),
        "b_price": unit_price,
        "total_mard": total_mard,
        "total_vbbe": total_vbbe,
        "actual_stock": actual_stock,
        "inventory_value": inventory_value,
        "fums_value": fums_value,
        "pan_india_coverage": pan_india_coverage,
        "frequency": random.choice(FREQUENCIES),
        "scenario": scenario,
        **monthly_forecasts,
        **monthly_stocks,
        **monthly_coverages,
    }

    return row


def inject_data_quality_issues(df: pl.DataFrame) -> pl.DataFrame:
    rows = df.to_dicts()

    # Missing supplier values
    for index in random.sample(range(len(rows)), k=20):
        rows[index]["supplier"] = None

    # Missing descriptions
    for index in random.sample(range(len(rows)), k=10):
        rows[index]["description"] = None

    # Duplicate records
    duplicates = random.sample(rows, k=5)
    rows.extend(duplicates)

    # Invalid coverage values similar to spreadsheet formula errors
    for index in random.sample(range(len(rows)), k=8):
        rows[index]["coverage"] = "#DIV/0!"

    # Simulate spreadsheet formatting artifacts
    for index in random.sample(range(len(rows)), k=8):
        rows[index]["description"] = (
            rows[index]["description"] or ""
        ) + "<br>"

    return pl.DataFrame(rows)


def main() -> None:
    data = [
        generate_row(index)
        for index in range(1, ROWS + 1)
    ]

    df = pl.DataFrame(data)
    df = inject_data_quality_issues(df)

    parquet_path = OUTPUT_DIR / "ppc_synthetic.parquet"
    csv_path = OUTPUT_DIR / "ppc_synthetic.csv"
    xlsx_path = OUTPUT_DIR / "ppc_synthetic.xlsx"

    df.write_parquet(parquet_path)
    df.write_csv(csv_path)

    # XLSX is intentionally generated as the portable demo format.
    # XLSB can later be used as an input format for the ingestion layer.
    import openpyxl

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "PPC Report"

    worksheet.append(df.columns)

    for row in df.iter_rows():
        worksheet.append(list(row))

    workbook.save(xlsx_path)

    print("=" * 70)
    print("Synthetic SAP PPC dataset generated")
    print("=" * 70)
    print(f"Rows       : {df.height:,}")
    print(f"Columns    : {df.width}")
    print(f"Parquet    : {parquet_path}")
    print(f"CSV        : {csv_path}")
    print(f"Excel      : {xlsx_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()