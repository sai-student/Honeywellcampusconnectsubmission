from pathlib import Path
import pandas as pd


INPUT_FILE = Path("results/python_baseline/eplusout.csv")
OUTPUT_FILE = Path("data/baseline_building.csv")

ZONES = [
    "SPACE1-1",
    "SPACE2-1",
    "SPACE3-1",
    "SPACE4-1",
    "SPACE5-1",
]


def process_baseline():

    print("Loading EnergyPlus results...")

    df = pd.read_csv(INPUT_FILE)

    # EnergyPlus sometimes adds spaces around column names
    df.columns = df.columns.str.strip()

    clean = pd.DataFrame()

    # -------------------------------------------------
    # TIME
    # -------------------------------------------------

    clean["timestamp"] = df["Date/Time"].astype(str).str.strip()

    # -------------------------------------------------
    # WEATHER
    # -------------------------------------------------

    clean["outdoor_temp_c"] = df[
        "Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)"
    ]

    # -------------------------------------------------
    # ZONE DATA
    # -------------------------------------------------

    for i, zone in enumerate(ZONES, start=1):

        clean[f"zone{i}_temp_c"] = df[
            f"{zone}:Zone Mean Air Temperature [C](Hourly)"
        ]

        clean[f"zone{i}_humidity_pct"] = df[
            f"{zone}:Zone Air Relative Humidity [%](Hourly)"
        ]

        clean[f"zone{i}_occupancy"] = df[
            f"{zone}:Zone People Occupant Count [](Hourly)"
        ]

        clean[f"zone{i}_heating_w"] = df[
            f"{zone}:Zone Air System Sensible Heating Rate [W](Hourly)"
        ]

        clean[f"zone{i}_cooling_w"] = df[
            f"{zone}:Zone Air System Sensible Cooling Rate [W](Hourly)"
        ]

    # -------------------------------------------------
    # ENERGY
    # EnergyPlus hourly meters are reported in Joules.
    #
    # 1 kWh = 3,600,000 J
    # -------------------------------------------------

    clean["facility_energy_kwh"] = (
        df["Electricity:Facility [J](Hourly)"] / 3_600_000
    )

    clean["hvac_energy_kwh"] = (
        df["Electricity:HVAC [J](Hourly)"] / 3_600_000
    )

    # -------------------------------------------------
    # CHILLER
    # -------------------------------------------------

    clean["chiller_power_w"] = df[
        "CENTRAL CHILLER:Chiller Electricity Rate [W](Hourly)"
    ]

    # -------------------------------------------------
    # AGGREGATED BUILDING STATE
    # -------------------------------------------------

    temp_columns = [
        f"zone{i}_temp_c"
        for i in range(1, 6)
    ]

    humidity_columns = [
        f"zone{i}_humidity_pct"
        for i in range(1, 6)
    ]

    occupancy_columns = [
        f"zone{i}_occupancy"
        for i in range(1, 6)
    ]

    clean["avg_indoor_temp_c"] = clean[temp_columns].mean(axis=1)

    clean["avg_humidity_pct"] = clean[
        humidity_columns
    ].mean(axis=1)

    clean["total_occupancy"] = clean[
        occupancy_columns
    ].sum(axis=1)

    # Difference between outdoor and indoor temperature
    clean["outdoor_indoor_delta_c"] = (
        clean["outdoor_temp_c"]
        - clean["avg_indoor_temp_c"]
    )

    # -------------------------------------------------
    # SAVE
    # -------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    clean.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nProcessing complete.")
    print(f"Rows: {len(clean)}")
    print(f"Columns: {len(clean.columns)}")
    print(f"Saved to: {OUTPUT_FILE}")

    print("\nFirst 5 rows:")
    print(clean.head())

    print("\nEnergy summary:")

    print(
        "Annual Facility Electricity:",
        round(clean["facility_energy_kwh"].sum(), 2),
        "kWh"
    )

    print(
        "Annual HVAC Electricity:",
        round(clean["hvac_energy_kwh"].sum(), 2),
        "kWh"
    )

    print(
        "Average Indoor Temperature:",
        round(clean["avg_indoor_temp_c"].mean(), 2),
        "°C"
    )


if __name__ == "__main__":
    process_baseline()