import pandas as pd
from pathlib import Path


FILES = {
    "Baseline": Path("results/python_baseline/eplusout.csv"),
    "Rule V1": Path("results/rule_v1/eplusout.csv"),
    "Rule V2": Path("results/rule_v2/eplusout.csv"),
    "Rule V3": Path("results/rule_v3/eplusout.csv"),
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


def evaluate(path):

    df = pd.read_csv(path)

    df.columns = df.columns.str.strip()


    # ========================================================
    # ELECTRICITY
    # ========================================================

    facility_kwh = (
        df["Electricity:Facility [J](Hourly)"].sum()
        / JOULES_PER_KWH
    )

    hvac_electricity_kwh = (
        df["Electricity:HVAC [J](Hourly)"].sum()
        / JOULES_PER_KWH
    )


    # ========================================================
    # NATURAL GAS
    #
    # This column is an hourly average rate in W.
    # Since each row represents one hour:
    #
    # W × 1 hour / 1000 = kWh
    #
    # This gives thermal fuel energy in kWh-equivalent.
    # ========================================================

    gas_column = (
        "CENTRAL BOILER:"
        "Boiler NaturalGas Rate [W](Hourly)"
    )

    natural_gas_kwh = (
        df[gas_column].sum() / 1000
    )


    # ========================================================
    # COMFORT
    # ========================================================

    occupied_zone_hours = 0
    comfortable_zone_hours = 0

    total_person_hours = 0
    comfortable_person_hours = 0

    person_temp_sum = 0


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


        occupied_zone_hours += occupied.sum()

        comfortable_zone_hours += (
            comfortable.sum()
        )


        total_person_hours += (
            occupancy[occupied].sum()
        )

        comfortable_person_hours += (
            occupancy[comfortable].sum()
        )


        person_temp_sum += (
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
        / total_person_hours
        * 100
    )


    avg_person_temp = (
        person_temp_sum
        / total_person_hours
    )


    return {

        "facility_kwh":
            facility_kwh,

        "hvac_electricity_kwh":
            hvac_electricity_kwh,

        "gas_kwh":
            natural_gas_kwh,

        "zone_comfort":
            zone_comfort,

        "person_comfort":
            person_comfort,

        "avg_person_temp":
            avg_person_temp
    }


# ============================================================
# CALCULATE
# ============================================================

results = {}

for name, path in FILES.items():

    if not path.exists():

        print(
            f"ERROR: Missing file: {path}"
        )

        raise SystemExit

    results[name] = evaluate(path)


baseline = results["Baseline"]


# ============================================================
# DISPLAY
# ============================================================

print("\n")
print("=" * 86)

print(
    "                 AI-BMS COMPLETE CONTROLLER EVALUATION"
)

print("=" * 86)


print(
    f"\n{'Controller':<12}"
    f"{'Facility':>13}"
    f"{'HVAC Elec':>13}"
    f"{'Gas':>13}"
    f"{'Person Comfort':>18}"
    f"{'Avg Temp':>12}"
)


print("-" * 86)


for name, m in results.items():

    print(
        f"{name:<12}"
        f"{m['facility_kwh']:>12.2f} "
        f"{m['hvac_electricity_kwh']:>12.2f} "
        f"{m['gas_kwh']:>12.2f} "
        f"{m['person_comfort']:>16.2f}% "
        f"{m['avg_person_temp']:>10.2f}C"
    )


# ============================================================
# SAVINGS
# ============================================================

print("\nENERGY SAVINGS RELATIVE TO BASELINE")
print("-" * 60)


for name, m in results.items():

    facility_saving = (
        (
            baseline["facility_kwh"]
            - m["facility_kwh"]
        )
        / baseline["facility_kwh"]
        * 100
    )


    hvac_saving = (
        (
            baseline["hvac_electricity_kwh"]
            - m["hvac_electricity_kwh"]
        )
        / baseline["hvac_electricity_kwh"]
        * 100
    )


    if baseline["gas_kwh"] > 0:

        gas_saving = (
            (
                baseline["gas_kwh"]
                - m["gas_kwh"]
            )
            / baseline["gas_kwh"]
            * 100
        )

    else:

        gas_saving = 0


    print(f"\n{name}")

    print(
        f"  Facility electricity : "
        f"{facility_saving:7.2f}%"
    )

    print(
        f"  HVAC electricity     : "
        f"{hvac_saving:7.2f}%"
    )

    print(
        f"  Natural gas          : "
        f"{gas_saving:7.2f}%"
    )


print("\n" + "=" * 86)