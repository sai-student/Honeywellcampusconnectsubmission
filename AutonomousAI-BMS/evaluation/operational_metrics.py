import csv
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_DIR = (
    PROJECT_ROOT
    / "results"
    / "evaluation"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


OPERATIONAL_FILE = (
    RESULTS_DIR
    / "ai_operational_metrics.csv"
)


CSV_HEADERS = [

    "timestamp",
    "simulation_time",

    "outdoor_temperature",
    "occupancy",

    "avg_occupied_temperature",
    "min_occupied_temperature",
    "max_occupied_temperature",

    "heating_setpoint",
    "cooling_setpoint",

    "hvac_power_kw",

    # Energy
    "hvac_electricity_kwh",
    "cooling_electricity_kwh",
    "fans_electricity_kwh",
    "pumps_electricity_kwh",

    "heating_natural_gas_kwh",

    "heating_demand_kwh",
    "cooling_demand_kwh",

    "total_hvac_site_energy_kwh",

    # Carbon
    "carbon_intensity",
    "carbon_level",

    "electricity_carbon_kg",
    "gas_carbon_kg",
    "total_hvac_carbon_kg",

    # Comfort
    "comfort_violation"
]


# ============================================================
# INITIALIZE FILE
# ============================================================

def initialize_operational_metrics():

    if OPERATIONAL_FILE.exists():
        return

    with open(
        OPERATIONAL_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=CSV_HEADERS
        )

        writer.writeheader()


# ============================================================
# COMFORT
# ============================================================

def calculate_comfort_violation(
    occupancy,
    min_temperature,
    max_temperature
):

    if occupancy <= 0:
        return 0

    if (
        min_temperature is None
        or max_temperature is None
    ):
        return 0

    if float(min_temperature) < 20.0:
        return 1

    if float(max_temperature) > 26.0:
        return 1

    return 0


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        return float(value)

    except (
        TypeError,
        ValueError
    ):

        return default


# ============================================================
# LOG OPERATIONAL METRICS
# ============================================================

def log_operational_metrics(
    simulation_time,
    building_state,
    heating_setpoint,
    cooling_setpoint,
    timestep_hours=0.25
):

    initialize_operational_metrics()


    # ========================================================
    # BUILDING STATE
    # ========================================================

    occupancy = safe_float(
        building_state.get(
            "total_occupancy"
        )
    )

    avg_temperature = building_state.get(
        "avg_occupied_temperature"
    )

    min_temperature = building_state.get(
        "min_occupied_temperature"
    )

    max_temperature = building_state.get(
        "max_occupied_temperature"
    )

    hvac_power_kw = safe_float(
        building_state.get(
            "hvac_power_kw"
        )
    )


    # ========================================================
    # ENERGY METERS
    # ========================================================

    hvac_electricity_kwh = safe_float(
        building_state.get(
            "hvac_electricity_kwh"
        )
    )

    cooling_electricity_kwh = safe_float(
        building_state.get(
            "cooling_electricity_kwh"
        )
    )

    fans_electricity_kwh = safe_float(
        building_state.get(
            "fans_electricity_kwh"
        )
    )

    pumps_electricity_kwh = safe_float(
        building_state.get(
            "pumps_electricity_kwh"
        )
    )

    heating_natural_gas_kwh = safe_float(
        building_state.get(
            "heating_natural_gas_kwh"
        )
    )

    heating_demand_kwh = safe_float(
        building_state.get(
            "heating_demand_kwh"
        )
    )

    cooling_demand_kwh = safe_float(
        building_state.get(
            "cooling_demand_kwh"
        )
    )


    # ========================================================
    # ELECTRICITY FALLBACK
    # ========================================================

    # Only use power integration if an EnergyPlus electricity
    # meter value is unavailable.
    #
    # Do NOT add fans/pumps/cooling electricity to HVAC
    # electricity because those meters may overlap.

    if hvac_electricity_kwh <= 0:

        hvac_electricity_kwh = (
            hvac_power_kw
            * timestep_hours
        )


    # ========================================================
    # TOTAL HVAC SITE ENERGY
    # ========================================================

    total_hvac_site_energy_kwh = (
        hvac_electricity_kwh
        +
        heating_natural_gas_kwh
    )


    # ========================================================
    # CARBON INFORMATION
    # ========================================================

    carbon_intensity = safe_float(
        building_state.get(
            "carbon_intensity"
        ),
        0.42
    )

    carbon_level = (
        building_state.get(
            "carbon_level",
            "moderate"
        )
        or "moderate"
    )


    # Natural-gas emission factor.
    #
    # kg CO2 / kWh of natural-gas site energy.
    #
    # Keep this identical to baseline_metrics.py.

    NATURAL_GAS_EMISSION_FACTOR = 0.181


    electricity_carbon_kg = (
        hvac_electricity_kwh
        * carbon_intensity
    )

    gas_carbon_kg = (
        heating_natural_gas_kwh
        * NATURAL_GAS_EMISSION_FACTOR
    )

    total_hvac_carbon_kg = (
        electricity_carbon_kg
        +
        gas_carbon_kg
    )


    # ========================================================
    # COMFORT
    # ========================================================

    comfort_violation = (
        calculate_comfort_violation(
            occupancy,
            min_temperature,
            max_temperature
        )
    )


    # ========================================================
    # CREATE ROW
    # ========================================================

    row = {

        "timestamp":
            datetime.now().isoformat(),

        "simulation_time":
            simulation_time,

        "outdoor_temperature":
            building_state.get(
                "outdoor_temperature"
            ),

        "occupancy":
            occupancy,

        "avg_occupied_temperature":
            avg_temperature,

        "min_occupied_temperature":
            min_temperature,

        "max_occupied_temperature":
            max_temperature,

        "heating_setpoint":
            heating_setpoint,

        "cooling_setpoint":
            cooling_setpoint,

        "hvac_power_kw":
            round(
                hvac_power_kw,
                6
            ),

        "hvac_electricity_kwh":
            round(
                hvac_electricity_kwh,
                6
            ),

        "cooling_electricity_kwh":
            round(
                cooling_electricity_kwh,
                6
            ),

        "fans_electricity_kwh":
            round(
                fans_electricity_kwh,
                6
            ),

        "pumps_electricity_kwh":
            round(
                pumps_electricity_kwh,
                6
            ),

        "heating_natural_gas_kwh":
            round(
                heating_natural_gas_kwh,
                6
            ),

        "heating_demand_kwh":
            round(
                heating_demand_kwh,
                6
            ),

        "cooling_demand_kwh":
            round(
                cooling_demand_kwh,
                6
            ),

        "total_hvac_site_energy_kwh":
            round(
                total_hvac_site_energy_kwh,
                6
            ),

        "carbon_intensity":
            round(
                carbon_intensity,
                6
            ),

        "carbon_level":
            str(
                carbon_level
            ).lower(),

        "electricity_carbon_kg":
            round(
                electricity_carbon_kg,
                6
            ),

        "gas_carbon_kg":
            round(
                gas_carbon_kg,
                6
            ),

        "total_hvac_carbon_kg":
            round(
                total_hvac_carbon_kg,
                6
            ),

        "comfort_violation":
            comfort_violation
    }


    # ========================================================
    # WRITE ROW
    # ========================================================

    with open(
        OPERATIONAL_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=CSV_HEADERS
        )

        writer.writerow(
            row
        )