import sys
from pathlib import Path


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# ENERGYPLUS PATH
# ============================================================

ENERGYPLUS_DIR = r"C:\EnergyPlusV26-1-0"

if ENERGYPLUS_DIR not in sys.path:
    sys.path.insert(0, ENERGYPLUS_DIR)


# ============================================================
# IMPORTS
# ============================================================

from pyenergyplus.api import EnergyPlusAPI

from evaluation.baseline_metrics import (
    initialize_baseline_metrics,
    log_baseline_metrics
)

from carbon.carbon_model import (
    get_carbon_intensity,
    get_carbon_level
)


# ============================================================
# PATHS
# ============================================================

MODEL = (
    PROJECT_ROOT
    / "building"
    / "models"
    / "5ZoneAI.idf"
)

WEATHER = (
    PROJECT_ROOT
    / "building"
    / "weather"
    / "chicago.epw"
)

OUTPUT = (
    PROJECT_ROOT
    / "results"
    / "baseline"
)

OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# BUILDING
# ============================================================

ZONES = [
    "SPACE1-1",
    "SPACE2-1",
    "SPACE3-1",
    "SPACE4-1",
    "SPACE5-1"
]

JOULES_TO_KWH = 1.0 / 3_600_000.0
NATURAL_GAS_CARBON_FACTOR = 0.181


# ============================================================
# BASELINE HVAC SETPOINTS
# ============================================================
#
# Conventional rule-based baseline.
#
# OCCUPIED:
# Heating = 20 C
# Cooling = 26 C
#
# UNOCCUPIED:
# Heating = 18 C
# Cooling = 29 C
#
# IMPORTANT:
# This controller does NOT use AI and does NOT use carbon
# intensity to change HVAC setpoints.
#
# Carbon intensity is measured/logged only so that the
# baseline and AI controller can be evaluated using the
# same grid-carbon profile.
# ============================================================

OCCUPIED_HEATING = 20.0
OCCUPIED_COOLING = 26.0

UNOCCUPIED_HEATING = 18.0
UNOCCUPIED_COOLING = 29.0


# ============================================================
# ENERGYPLUS
# ============================================================

api = EnergyPlusAPI()

state = api.state_manager.new_state()


# ============================================================
# HANDLES
# ============================================================

handles = {

    "initialized": False,

    "heating_actuator": -1,
    "cooling_actuator": -1,

    "outdoor_temp": -1,

    "zone_temps": [],
    "occupancies": [],

    "hvac_electricity": -1,
    "cooling_electricity": -1,
    "heating_natural_gas": -1,
    "fans_electricity": -1,
    "pumps_electricity": -1,
    "heating_demand": -1,
    "cooling_demand": -1
}


# ============================================================
# BASELINE STATE
# ============================================================

baseline_state = {

    "heating": OCCUPIED_HEATING,
    "cooling": OCCUPIED_COOLING,

    "last_metrics_hour": None,

    "metrics_logged": 0
}


# ============================================================
# SIMULATION TIME
# ============================================================

def get_simulation_time(state_argument):

    month = api.exchange.month(
        state_argument
    )

    day = api.exchange.day_of_month(
        state_argument
    )

    hour = api.exchange.hour(
        state_argument
    )

    minute = api.exchange.minutes(
        state_argument
    )

    return (
        f"{month:02d}/"
        f"{day:02d} "
        f"{hour:02d}:"
        f"{minute:02d}"
    )


# ============================================================
# ENERGY / METER HELPERS
# ============================================================

def safe_get_meter_handle(state_argument, meter_name):
    try:
        handle = api.exchange.get_meter_handle(
            state_argument,
            meter_name
        )
    except Exception as error:
        print(f"[METER ERROR] {meter_name}: {error}")
        return -1

    if handle == -1:
        print(f"[METER MISSING] {meter_name}")
    else:
        print(f"[METER OK] {meter_name}: {handle}")

    return handle


def read_meter_kwh(state_argument, handle):
    if handle == -1:
        return 0.0

    try:
        value_j = api.exchange.get_meter_value(
            state_argument,
            handle
        )
        return max(0.0, float(value_j) * JOULES_TO_KWH)
    except Exception:
        return 0.0


def read_energy_state(state_argument):
    """
    Electricity:HVAC is the aggregate electrical HVAC meter.
    Cooling/Fans/Pumps are diagnostic sub-meters and are not
    added again to Electricity:HVAC.

    Natural-gas heating is a separate energy carrier and is
    therefore added to HVAC electricity for total site energy.
    """

    hvac_electricity_kwh = read_meter_kwh(
        state_argument,
        handles["hvac_electricity"]
    )

    cooling_electricity_kwh = read_meter_kwh(
        state_argument,
        handles["cooling_electricity"]
    )

    heating_natural_gas_kwh = read_meter_kwh(
        state_argument,
        handles["heating_natural_gas"]
    )

    fans_electricity_kwh = read_meter_kwh(
        state_argument,
        handles["fans_electricity"]
    )

    pumps_electricity_kwh = read_meter_kwh(
        state_argument,
        handles["pumps_electricity"]
    )

    heating_demand_kwh = read_meter_kwh(
        state_argument,
        handles["heating_demand"]
    )

    cooling_demand_kwh = read_meter_kwh(
        state_argument,
        handles["cooling_demand"]
    )

    total_hvac_site_energy_kwh = (
        hvac_electricity_kwh
        + heating_natural_gas_kwh
    )

    return {
        "hvac_electricity_kwh": round(hvac_electricity_kwh, 6),
        "cooling_electricity_kwh": round(cooling_electricity_kwh, 6),
        "heating_natural_gas_kwh": round(heating_natural_gas_kwh, 6),
        "fans_electricity_kwh": round(fans_electricity_kwh, 6),
        "pumps_electricity_kwh": round(pumps_electricity_kwh, 6),
        "heating_demand_kwh": round(heating_demand_kwh, 6),
        "cooling_demand_kwh": round(cooling_demand_kwh, 6),
        "total_hvac_site_energy_kwh": round(total_hvac_site_energy_kwh, 6)
    }


def calculate_hvac_carbon(energy_state, carbon_intensity):
    electricity_carbon_kg = (
        float(energy_state["hvac_electricity_kwh"])
        * float(carbon_intensity)
    )

    gas_carbon_kg = (
        float(energy_state["heating_natural_gas_kwh"])
        * NATURAL_GAS_CARBON_FACTOR
    )

    return {
        "electricity_carbon_kg": round(electricity_carbon_kg, 6),
        "gas_carbon_kg": round(gas_carbon_kg, 6),
        "total_hvac_carbon_kg": round(
            electricity_carbon_kg + gas_carbon_kg,
            6
        )
    }


# ============================================================
# BASELINE CALLBACK
# ============================================================

def baseline_callback(state_argument):

    # ========================================================
    # WAIT FOR ENERGYPLUS
    # ========================================================

    if not api.exchange.api_data_fully_ready(
        state_argument
    ):
        return


    # ========================================================
    # INITIALIZE HANDLES
    # ========================================================

    if not handles["initialized"]:

        print(
            "\nInitializing baseline controller handles..."
        )


        # ----------------------------------------------------
        # HEATING ACTUATOR
        # ----------------------------------------------------

        handles["heating_actuator"] = (
            api.exchange.get_actuator_handle(
                state_argument,
                "Schedule:Compact",
                "Schedule Value",
                "HTG-SETP-SCH"
            )
        )


        # ----------------------------------------------------
        # COOLING ACTUATOR
        # ----------------------------------------------------

        handles["cooling_actuator"] = (
            api.exchange.get_actuator_handle(
                state_argument,
                "Schedule:Compact",
                "Schedule Value",
                "CLG-SETP-SCH"
            )
        )


        # ----------------------------------------------------
        # OUTDOOR TEMPERATURE
        # ----------------------------------------------------

        handles["outdoor_temp"] = (
            api.exchange.get_variable_handle(
                state_argument,
                "Site Outdoor Air Drybulb Temperature",
                "Environment"
            )
        )


        # ----------------------------------------------------
        # RESET ZONE HANDLES
        # ----------------------------------------------------

        handles["zone_temps"] = []
        handles["occupancies"] = []


        # ----------------------------------------------------
        # ZONE HANDLES
        # ----------------------------------------------------

        for zone in ZONES:

            temperature_handle = (
                api.exchange.get_variable_handle(
                    state_argument,
                    "Zone Mean Air Temperature",
                    zone
                )
            )

            occupancy_handle = (
                api.exchange.get_variable_handle(
                    state_argument,
                    "Zone People Occupant Count",
                    zone
                )
            )

            handles[
                "zone_temps"
            ].append(
                temperature_handle
            )

            handles[
                "occupancies"
            ].append(
                occupancy_handle
            )


        # ----------------------------------------------------
        # HVAC ENERGY METERS
        # ----------------------------------------------------

        meter_names = {
            "hvac_electricity": "Electricity:HVAC",
            "cooling_electricity": "Cooling:Electricity",
            "heating_natural_gas": "Heating:NaturalGas",
            "fans_electricity": "Fans:Electricity",
            "pumps_electricity": "Pumps:Electricity",
            "heating_demand": "PlantLoopHeatingDemand:HVAC",
            "cooling_demand": "PlantLoopCoolingDemand:HVAC"
        }

        for key, meter_name in meter_names.items():
            handles[key] = safe_get_meter_handle(
                state_argument,
                meter_name
            )


        # ----------------------------------------------------
        # DEBUG OUTPUT
        # ----------------------------------------------------

        print(
            "Heating actuator:",
            handles["heating_actuator"]
        )

        print(
            "Cooling actuator:",
            handles["cooling_actuator"]
        )

        print(
            "Outdoor temperature:",
            handles["outdoor_temp"]
        )

        print(
            "Zone temperatures:",
            handles["zone_temps"]
        )

        print(
            "Occupancies:",
            handles["occupancies"]
        )

        print("Energy meter handles:")
        for meter_key in [
            "hvac_electricity",
            "cooling_electricity",
            "heating_natural_gas",
            "fans_electricity",
            "pumps_electricity",
            "heating_demand",
            "cooling_demand"
        ]:
            print(
                f"  {meter_key}:",
                handles[meter_key]
            )


        # ----------------------------------------------------
        # VALIDATE REQUIRED HANDLES
        # ----------------------------------------------------

        required_handles = (

            [
                handles["heating_actuator"],
                handles["cooling_actuator"],
                handles["outdoor_temp"]
            ]

            + handles["zone_temps"]

            + handles["occupancies"]
        )


        if any(
            handle == -1
            for handle in required_handles
        ):

            print(
                "\nERROR: One or more EnergyPlus "
                "handles are invalid."
            )

            return


        handles["initialized"] = True


        print(
            "\nBaseline controller initialized."
        )


    # ========================================================
    # IGNORE ENERGYPLUS WARMUP
    # ========================================================

    if api.exchange.warmup_flag(
        state_argument
    ):
        return


    # ========================================================
    # READ OUTDOOR TEMPERATURE
    # ========================================================

    outdoor_temperature = (
        api.exchange.get_variable_value(
            state_argument,
            handles["outdoor_temp"]
        )
    )


    # ========================================================
    # READ ZONE TEMPERATURES
    # ========================================================

    zone_temperatures = [

        api.exchange.get_variable_value(
            state_argument,
            handle
        )

        for handle
        in handles["zone_temps"]
    ]


    # ========================================================
    # READ OCCUPANCIES
    # ========================================================

    occupancies = [

        api.exchange.get_variable_value(
            state_argument,
            handle
        )

        for handle
        in handles["occupancies"]
    ]


    total_occupancy = sum(
        occupancies
    )


    # ========================================================
    # RULE-BASED BASELINE CONTROL
    # ========================================================

    if total_occupancy > 0:

        heating_setpoint = (
            OCCUPIED_HEATING
        )

        cooling_setpoint = (
            OCCUPIED_COOLING
        )

    else:

        heating_setpoint = (
            UNOCCUPIED_HEATING
        )

        cooling_setpoint = (
            UNOCCUPIED_COOLING
        )


    baseline_state[
        "heating"
    ] = heating_setpoint

    baseline_state[
        "cooling"
    ] = cooling_setpoint


    # ========================================================
    # APPLY BASELINE HVAC SETPOINTS
    # ========================================================

    api.exchange.set_actuator_value(

        state_argument,

        handles[
            "heating_actuator"
        ],

        heating_setpoint
    )


    api.exchange.set_actuator_value(

        state_argument,

        handles[
            "cooling_actuator"
        ],

        cooling_setpoint
    )


    # ========================================================
    # OCCUPIED TEMPERATURE STATISTICS
    # ========================================================

    occupied_temperatures = [

        temperature

        for temperature, occupancy
        in zip(
            zone_temperatures,
            occupancies
        )

        if occupancy > 0
    ]


    if occupied_temperatures:

        avg_temp = (
            sum(
                occupied_temperatures
            )
            / len(
                occupied_temperatures
            )
        )

        min_temp = min(
            occupied_temperatures
        )

        max_temp = max(
            occupied_temperatures
        )

    else:

        avg_temp = None
        min_temp = None
        max_temp = None


    # ========================================================
    # HVAC ENERGY + POWER
    # ========================================================

    energy_state = read_energy_state(
        state_argument
    )

    try:
        timestep_hours = float(
            api.exchange.zone_time_step(
                state_argument
            )
        )
    except Exception:
        timestep_hours = 0.0

    if timestep_hours > 0:
        hvac_power_kw = (
            energy_state["hvac_electricity_kwh"]
            / timestep_hours
        )
    else:
        hvac_power_kw = 0.0

    hvac_power_kw = round(
        hvac_power_kw,
        4
    )


    # ========================================================
    # SIMULATION TIME
    # ========================================================

    simulation_time = (
        get_simulation_time(
            state_argument
        )
    )


    month = api.exchange.month(
        state_argument
    )

    day = api.exchange.day_of_month(
        state_argument
    )

    hour = api.exchange.hour(
        state_argument
    )


    # ========================================================
    # DYNAMIC GRID CARBON SIGNAL
    # ========================================================
    #
    # IMPORTANT:
    #
    # Baseline receives the SAME carbon-intensity profile
    # as the AI controller.
    #
    # However, baseline HVAC decisions do NOT depend on it.
    #
    # This keeps the comparison scientifically fair.
    # ========================================================

    try:

        carbon_intensity = float(
            get_carbon_intensity(
                hour=hour,
                month=month
            )
        )

        carbon_level = (
            get_carbon_level(
                carbon_intensity
            )
        )

    except Exception as carbon_error:

        print(
            "\nWARNING: Carbon model failed:",
            carbon_error
        )

        # Fail-safe carbon value for logging only.
        carbon_intensity = 0.42
        carbon_level = "moderate"


    carbon_intensity = round(
        carbon_intensity,
        4
    )


    # ========================================================
    # HVAC OPERATIONAL CARBON
    # ========================================================

    carbon_state = calculate_hvac_carbon(
        energy_state,
        carbon_intensity
    )


    # ========================================================
    # BUILDING STATE
    # ========================================================

    building_state = {

        "status":
            "running",

        "simulation_time":
            simulation_time,

        "outdoor_temperature":
            round(
                float(
                    outdoor_temperature
                ),
                2
            ),

        "total_occupancy":
            round(
                float(
                    total_occupancy
                ),
                2
            ),

        "avg_occupied_temperature": (
            round(
                float(
                    avg_temp
                ),
                2
            )

            if avg_temp is not None

            else None
        ),

        "min_occupied_temperature": (
            round(
                float(
                    min_temp
                ),
                2
            )

            if min_temp is not None

            else None
        ),

        "max_occupied_temperature": (
            round(
                float(
                    max_temp
                ),
                2
            )

            if max_temp is not None

            else None
        ),

        "current_setpoints": {

            "heating":
                heating_setpoint,

            "cooling":
                cooling_setpoint
        },

        "hvac_power_kw":
            hvac_power_kw,

        # Backward-compatible electrical HVAC field.
        "hvac_energy_kwh":
            energy_state["hvac_electricity_kwh"],

        "hvac_electricity_kwh":
            energy_state["hvac_electricity_kwh"],

        "cooling_electricity_kwh":
            energy_state["cooling_electricity_kwh"],

        "heating_natural_gas_kwh":
            energy_state["heating_natural_gas_kwh"],

        "fans_electricity_kwh":
            energy_state["fans_electricity_kwh"],

        "pumps_electricity_kwh":
            energy_state["pumps_electricity_kwh"],

        "heating_demand_kwh":
            energy_state["heating_demand_kwh"],

        "cooling_demand_kwh":
            energy_state["cooling_demand_kwh"],

        "total_hvac_site_energy_kwh":
            energy_state["total_hvac_site_energy_kwh"],

        "carbon_intensity":
            carbon_intensity,

        "carbon_level":
            carbon_level,

        "electricity_carbon_kg":
            carbon_state["electricity_carbon_kg"],

        "gas_carbon_kg":
            carbon_state["gas_carbon_kg"],

        "total_hvac_carbon_kg":
            carbon_state["total_hvac_carbon_kg"],

        # Backward-compatible carbon field.
        "hvac_carbon_kg":
            carbon_state["total_hvac_carbon_kg"]
    }


    # ========================================================
    # HOURLY METRICS
    # ========================================================

    metrics_key = (
        month,
        day,
        hour
    )


    if (
        baseline_state[
            "last_metrics_hour"
        ]
        != metrics_key
    ):

        try:

            timestep_hours = float(
                api.exchange.zone_time_step(
                    state_argument
                )
            )


            log_baseline_metrics(

                simulation_time=
                    simulation_time,

                building_state=
                    building_state,

                heating_setpoint=
                    heating_setpoint,

                cooling_setpoint=
                    cooling_setpoint,

                timestep_hours=
                    timestep_hours
            )


            baseline_state[
                "last_metrics_hour"
            ] = metrics_key


            baseline_state[
                "metrics_logged"
            ] += 1


            # ------------------------------------------------
            # PERIODIC CONSOLE REPORT
            # ------------------------------------------------

            print(
                "\n----------------------------------------"
            )

            print(
                "[BASELINE]",
                simulation_time
            )

            print(
                "Outdoor:",
                round(
                    outdoor_temperature,
                    2
                ),
                "C"
            )

            print(
                "Occupancy:",
                round(
                    total_occupancy,
                    2
                )
            )

            print(
                "Setpoints:",
                heating_setpoint,
                "/",
                cooling_setpoint
            )

            print(
                "HVAC power:",
                hvac_power_kw,
                "kW"
            )


            print(
                "HVAC electricity:",
                energy_state["hvac_electricity_kwh"],
                "kWh"
            )

            print(
                "Cooling electricity:",
                energy_state["cooling_electricity_kwh"],
                "kWh"
            )

            print(
                "Heating natural gas:",
                energy_state["heating_natural_gas_kwh"],
                "kWh"
            )

            print(
                "Fan electricity:",
                energy_state["fans_electricity_kwh"],
                "kWh"
            )

            print(
                "Pump electricity:",
                energy_state["pumps_electricity_kwh"],
                "kWh"
            )

            print(
                "Heating demand:",
                energy_state["heating_demand_kwh"],
                "kWh"
            )

            print(
                "Cooling demand:",
                energy_state["cooling_demand_kwh"],
                "kWh"
            )

            print(
                "Total HVAC site energy:",
                energy_state["total_hvac_site_energy_kwh"],
                "kWh"
            )

            print(
                "Carbon intensity:",
                carbon_intensity,
                "kg CO2/kWh"
            )

            print(
                "Carbon level:",
                str(
                    carbon_level
                ).upper()
            )


            print(
                "Electricity carbon:",
                carbon_state["electricity_carbon_kg"],
                "kg CO2"
            )

            print(
                "Gas carbon:",
                carbon_state["gas_carbon_kg"],
                "kg CO2"
            )

            print(
                "Total HVAC carbon:",
                carbon_state["total_hvac_carbon_kg"],
                "kg CO2"
            )


            if (
                min_temp is not None
                and max_temp is not None
            ):

                print(
                    "Occupied temperature:",
                    round(
                        min_temp,
                        2
                    ),
                    "-",
                    round(
                        max_temp,
                        2
                    ),
                    "C"
                )


        except Exception as error:

            print(
                "\nBaseline metrics error:",
                error
            )


# ============================================================
# REGISTER CALLBACK
# ============================================================

api.runtime.callback_begin_zone_timestep_after_init_heat_balance(
    state,
    baseline_callback
)


# ============================================================
# INITIALIZE METRICS
# ============================================================

initialize_baseline_metrics()


# ============================================================
# ENERGYPLUS ARGUMENTS
# ============================================================

arguments = [

    "-r",

    "-w",
    str(WEATHER),

    "-d",
    str(OUTPUT),

    str(MODEL)
]


# ============================================================
# START INFORMATION
# ============================================================

print(
    "\n============================================"
)

print(
    "       BASELINE BMS SIMULATION"
)

print(
    "============================================"
)


print(
    "\nModel:",
    MODEL
)

print(
    "\nWeather:",
    WEATHER
)

print(
    "\nOutput:",
    OUTPUT
)


print(
    "\nController      : Conventional Rule-Based BMS"
)

print(
    "AI              : DISABLED"
)

print(
    "Semantic Guard  : DISABLED"
)

print(
    "Safety Guard    : DISABLED"
)

print(
    "Carbon Control  : DISABLED"
)

print(
    "Dynamic Carbon  : ENABLED FOR MEASUREMENT"
)

print(
    "Occupied        : 20 C / 26 C"
)

print(
    "Unoccupied      : 18 C / 29 C"
)

print(
    "Metrics         : ENABLED"
)

print(
    "Energy Metering : ELECTRIC + NATURAL GAS"
)

print(
    "Carbon Accounting: GRID ELECTRICITY + NATURAL GAS"
)


print(
    "\nStarting baseline simulation...\n"
)


# ============================================================
# RUN ENERGYPLUS
# ============================================================

exit_code = (
    api.runtime.run_energyplus(
        state,
        arguments
    )
)


# ============================================================
# FINAL REPORT
# ============================================================

print(
    "\n============================================"
)


if exit_code == 0:

    print(
        "Baseline simulation completed successfully."
    )

else:

    print(
        "Baseline simulation FAILED."
    )

    print(
        "Exit code:",
        exit_code
    )


print(
    "\nFinal heating setpoint:",
    baseline_state[
        "heating"
    ]
)

print(
    "Final cooling setpoint:",
    baseline_state[
        "cooling"
    ]
)

print(
    "Hourly metric records:",
    baseline_state[
        "metrics_logged"
    ]
)


print(
    "============================================"
)