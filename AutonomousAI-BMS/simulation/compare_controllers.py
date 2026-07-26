import pandas as pd
from pathlib import Path

FILES = {
    "Baseline": Path("results/python_baseline/eplusout.csv"),
    "Rule V1": Path("results/rule_v1/eplusout.csv"),
    "Rule V2": Path("results/rule_v2/eplusout.csv"),
}

ZONES = [
    "SPACE1-1",
    "SPACE2-1",
    "SPACE3-1",
    "SPACE4-1",
    "SPACE5-1",
]

JOULES_PER_KWH = 3_600_000

COMFORT_MIN = 22.0
COMFORT_MAX = 26.0


def calculate_metrics(path):

    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    # -----------------------------
    # ENERGY
    # -----------------------------

    facility_kwh = (
        df["Electricity:Facility [J](Hourly)"].sum()
        / JOULES_PER_KWH
    )

    hvac_kwh = (
        df["Electricity:HVAC [J](Hourly)"].sum()
        / JOULES_PER_KWH
    )

    # -----------------------------
    # COMFORT
    # -----------------------------

    occupied_zone_hours = 0
    comfortable_zone_hours = 0

    occupied_person_hours = 0
    comfortable_person_hours = 0

    temp_person_sum = 0

    for zone in ZONES:

        occupancy = df[
            f"{zone}:Zone People Occupant Count [](Hourly)"
        ]

        temperature = df[
            f"{zone}:Zone Mean Air Temperature [C](Hourly)"
        ]

        occupied = occupancy > 0

        comfortable = (
            occupied
            & (temperature >= COMFORT_MIN)
            & (temperature <= COMFORT_MAX)
        )

        # Zone-hour comfort
        occupied_zone_hours += occupied.sum()
        comfortable_zone_hours += comfortable.sum()

        # Person-hour comfort
        occupied_person_hours += occupancy[occupied].sum()

        comfortable_person_hours += (
            occupancy[comfortable].sum()
        )

        # Occupancy-weighted temperature
        temp_person_sum += (
            temperature[occupied]
            * occupancy[occupied]
        ).sum()

    zone_comfort = (
        comfortable_zone_hours
        / occupied_zone_hours
        * 100
    )

    person_comfort = (
        comfortable_person_hours
        / occupied_person_hours
        * 100
    )

    avg_person_temp = (
        temp_person_sum
        / occupied_person_hours
    )

    return {
        "facility": facility_kwh,
        "hvac": hvac_kwh,
        "zone_comfort": zone_comfort,
        "person_comfort": person_comfort,
        "avg_person_temp": avg_person_temp,
        "occupied_zone_hours": occupied_zone_hours,
        "person_hours": occupied_person_hours,
    }


results = {}

for name, path in FILES.items():

    if not path.exists():
        print(f"ERROR: Missing {path}")
        exit()

    results[name] = calculate_metrics(path)


baseline = results["Baseline"]


print("\n============================================================")
print("             AI-BMS CONTROLLER EVALUATION")
print("============================================================")

print(
    f"\n{'Controller':<15}"
    f"{'Facility kWh':>15}"
    f"{'HVAC kWh':>15}"
    f"{'HVAC Save':>12}"
)

print("-" * 57)

for name, metrics in results.items():

    hvac_saving = (
        (baseline["hvac"] - metrics["hvac"])
        / baseline["hvac"]
        * 100
    )

    print(
        f"{name:<15}"
        f"{metrics['facility']:>15.2f}"
        f"{metrics['hvac']:>15.2f}"
        f"{hvac_saving:>11.2f}%"
    )


print("\nCOMFORT")
print("-" * 70)

print(
    f"{'Controller':<15}"
    f"{'Zone Comfort':>15}"
    f"{'Person Comfort':>17}"
    f"{'Avg Person Temp':>18}"
)

for name, metrics in results.items():

    print(
        f"{name:<15}"
        f"{metrics['zone_comfort']:>14.2f}%"
        f"{metrics['person_comfort']:>16.2f}%"
        f"{metrics['avg_person_temp']:>16.2f} C"
    )


print("\nFACILITY SAVINGS")
print("-" * 40)

for name, metrics in results.items():

    saving = (
        (baseline["facility"] - metrics["facility"])
        / baseline["facility"]
        * 100
    )

    print(
        f"{name:<15}: {saving:.2f}%"
    )


print("\n============================================================")