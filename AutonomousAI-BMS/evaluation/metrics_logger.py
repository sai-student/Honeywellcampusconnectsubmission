import csv
from pathlib import Path
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

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

AI_METRICS_FILE = (
    RESULTS_DIR
    / "ai_metrics.csv"
)


# ============================================================
# CSV SCHEMA
# ============================================================

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

    # --------------------------------------------------------
    # ELECTRICAL HVAC ENERGY
    # --------------------------------------------------------

    "hvac_electricity_kwh",
    "cooling_electricity_kwh",
    "fans_electricity_kwh",
    "pumps_electricity_kwh",

    # --------------------------------------------------------
    # NATURAL GAS
    # --------------------------------------------------------

    "heating_natural_gas_kwh",

    # --------------------------------------------------------
    # THERMAL DEMAND
    # --------------------------------------------------------

    "heating_demand_kwh",
    "cooling_demand_kwh",

    # --------------------------------------------------------
    # TOTAL HVAC SITE ENERGY
    # --------------------------------------------------------

    "total_hvac_site_energy_kwh",

    # --------------------------------------------------------
    # CARBON
    # --------------------------------------------------------

    "carbon_intensity",
    "carbon_level",

    "electricity_carbon_kg",
    "gas_carbon_kg",
    "total_hvac_carbon_kg",

    # --------------------------------------------------------
    # COMFORT
    # --------------------------------------------------------

    "comfort_violation",

    # --------------------------------------------------------
    # AI INFORMATION
    # --------------------------------------------------------

    "ai_call",

    "semantic_modified",
    "semantic_correction_count",

    "safety_modified",
    "safety_correction_count"
]


# ============================================================
# INITIALIZE CSV
# ============================================================

def initialize_metrics_file():

    if AI_METRICS_FILE.exists():
        return

    with open(
        AI_METRICS_FILE,
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
# SAFE FLOAT
# ============================================================

def safe_float(
    value,
    default=0.0
):

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
# COMFORT VIOLATION
# ============================================================

def calculate_comfort_violation(
    occupancy,
    min_temperature,
    max_temperature
):
    """
    Occupied comfort range:

        20 C <= temperature <= 26 C

    Returns:

        1 -> comfort violation
        0 -> acceptable / unoccupied
    """

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
# AI METRICS LOGGER
# ============================================================

def log_ai_metrics(
    simulation_time,
    building_state,
    safe_action,
    ai_call_number
):

    initialize_metrics_file()


    # ========================================================
    # BUILDING CONDITIONS
    # ========================================================

    occupancy = safe_float(
        building_state.get(
            "total_occupancy"
        )
    )

    avg_temp = building_state.get(
        "avg_occupied_temperature"
    )

    min_temp = building_state.get(
        "min_occupied_temperature"
    )

    max_temp = building_state.get(
        "max_occupied_temperature"
    )


    # ========================================================
    # HVAC POWER
    # ========================================================

    hvac_power_kw = safe_float(
        building_state.get(
            "hvac_power_kw"
        )
    )


    # ========================================================
    # ELECTRICAL HVAC ENERGY
    # ========================================================

    hvac_electricity_kwh = safe_float(
        building_state.get(
            "hvac_electricity_kwh",
            building_state.get(
                "hvac_energy_kwh",
                0
            )
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


    # ========================================================
    # NATURAL GAS
    # ========================================================

    heating_natural_gas_kwh = safe_float(
        building_state.get(
            "heating_natural_gas_kwh"
        )
    )


    # ========================================================
    # THERMAL DEMAND
    # ========================================================

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
    # TOTAL HVAC SITE ENERGY
    # ========================================================

    total_hvac_site_energy_kwh = safe_float(
        building_state.get(
            "total_hvac_site_energy_kwh"
        )
    )

    # Fallback if total wasn't supplied by run_ai_control.py.
    #
    # Electricity:HVAC already contains electrical HVAC
    # end uses, so do NOT add cooling/fans/pumps again.

    if (
        total_hvac_site_energy_kwh <= 0
        and (
            hvac_electricity_kwh > 0
            or heating_natural_gas_kwh > 0
        )
    ):

        total_hvac_site_energy_kwh = (
            hvac_electricity_kwh
            + heating_natural_gas_kwh
        )


    # ========================================================
    # CARBON
    # ========================================================

    carbon_intensity = safe_float(
        building_state.get(
            "carbon_intensity"
        ),
        0.42
    )

    carbon_level = str(
        building_state.get(
            "carbon_level",
            "unknown"
        )
    )

    electricity_carbon_kg = safe_float(
        building_state.get(
            "electricity_carbon_kg"
        )
    )

    gas_carbon_kg = safe_float(
        building_state.get(
            "gas_carbon_kg"
        )
    )

    total_hvac_carbon_kg = safe_float(
        building_state.get(
            "total_hvac_carbon_kg",
            building_state.get(
                "hvac_carbon_kg",
                0
            )
        )
    )


    # --------------------------------------------------------
    # ELECTRICITY CARBON FALLBACK
    # --------------------------------------------------------

    if (
        electricity_carbon_kg <= 0
        and hvac_electricity_kwh > 0
    ):

        electricity_carbon_kg = (
            hvac_electricity_kwh
            * carbon_intensity
        )


    # --------------------------------------------------------
    # TOTAL CARBON FALLBACK
    # --------------------------------------------------------

    if (
        total_hvac_carbon_kg <= 0
        and (
            electricity_carbon_kg > 0
            or gas_carbon_kg > 0
        )
    ):

        total_hvac_carbon_kg = (
            electricity_carbon_kg
            + gas_carbon_kg
        )


    # ========================================================
    # COMFORT
    # ========================================================

    comfort_violation = (
        calculate_comfort_violation(
            occupancy,
            min_temp,
            max_temp
        )
    )


    # ========================================================
    # SEMANTIC GUARD
    # ========================================================

    semantic_corrections = (
        safe_action.get(
            "semantic_corrections",
            []
        )
        or []
    )


    # ========================================================
    # SAFETY GUARD
    # ========================================================

    safety_corrections = (
        safe_action.get(
            "reasons",
            []
        )
        or []
    )


    # ========================================================
    # CREATE CSV ROW
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
            round(
                occupancy,
                4
            ),

        "avg_occupied_temperature":
            avg_temp,

        "min_occupied_temperature":
            min_temp,

        "max_occupied_temperature":
            max_temp,

        "heating_setpoint":
            safe_action.get(
                "heating_setpoint"
            ),

        "cooling_setpoint":
            safe_action.get(
                "cooling_setpoint"
            ),

        "hvac_power_kw":
            round(
                hvac_power_kw,
                6
            ),

        # ====================================================
        # ELECTRICAL ENERGY
        # ====================================================

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

        # ====================================================
        # NATURAL GAS
        # ====================================================

        "heating_natural_gas_kwh":
            round(
                heating_natural_gas_kwh,
                6
            ),

        # ====================================================
        # THERMAL DEMAND
        # ====================================================

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

        # ====================================================
        # TOTAL HVAC SITE ENERGY
        # ====================================================

        "total_hvac_site_energy_kwh":
            round(
                total_hvac_site_energy_kwh,
                6
            ),

        # ====================================================
        # CARBON
        # ====================================================

        "carbon_intensity":
            round(
                carbon_intensity,
                6
            ),

        "carbon_level":
            carbon_level,

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

        # ====================================================
        # COMFORT
        # ====================================================

        "comfort_violation":
            comfort_violation,

        # ====================================================
        # AI
        # ====================================================

        "ai_call":
            ai_call_number,

        "semantic_modified":
            bool(
                safe_action.get(
                    "semantic_modified",
                    False
                )
            ),

        "semantic_correction_count":
            len(
                semantic_corrections
            ),

        "safety_modified":
            bool(
                safe_action.get(
                    "modified",
                    False
                )
            ),

        "safety_correction_count":
            len(
                safety_corrections
            )
    }


    # ========================================================
    # WRITE CSV
    # ========================================================

    with open(
        AI_METRICS_FILE,
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