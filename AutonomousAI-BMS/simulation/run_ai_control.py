import sys
from pathlib import Path
from datetime import date


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

from ai_engine.safe_ai_controller import (
    get_safe_ai_action
)

from ai_engine.live_decision_bridge import (
    write_live_ai_decision
)

from simulation.state_bridge import (
    write_building_state
)

from evaluation.metrics_logger import (
    log_ai_metrics,
    initialize_metrics_file
)

from evaluation.operational_metrics import (
    log_operational_metrics,
    initialize_operational_metrics
)

from carbon.carbon_model import (
    get_carbon_intensity,
    get_carbon_level
)


# ============================================================
# FILE PATHS
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
    / "ai_control"
)

OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# ENERGYPLUS INITIALIZATION
# ============================================================

api = EnergyPlusAPI()

state = api.state_manager.new_state()


# ============================================================
# BUILDING CONFIGURATION
# ============================================================

ZONES = [
    "SPACE1-1",
    "SPACE2-1",
    "SPACE3-1",
    "SPACE4-1",
    "SPACE5-1"
]

# Natural gas carbon factor:
# kg CO2 per kWh of natural-gas site energy.
NATURAL_GAS_CARBON_FACTOR = 0.181

JOULES_TO_KWH = 1.0 / 3_600_000.0


# ============================================================
# ENERGYPLUS HANDLES
# ============================================================

handles = {

    "initialized": False,

    "heating_actuator": -1,
    "cooling_actuator": -1,

    "outdoor_temp": -1,

    "zone_temps": [],
    "occupancies": [],

    # Energy meters
    "electricity_hvac": -1,
    "cooling_electricity": -1,
    "heating_natural_gas": -1,
    "fans_electricity": -1,
    "pumps_electricity": -1,
    "heating_demand": -1,
    "cooling_demand": -1
}


# ============================================================
# CONTROLLER STATE
# ============================================================

controller_state = {

    "heating": 20.0,
    "cooling": 25.0,

    "last_ai_interval": None,

    # LLM remains supervisory.
    "ai_interval_hours": 6,

    # Operational metrics once per simulated hour.
    "last_metrics_hour": None,

    "ai_calls": 0,
    "ai_failures": 0,

    "safety_interventions": 0,
    "semantic_interventions": 0,

    # Fast local guard statistics.
    "comfort_guard_interventions": 0,

    "last_safe_action": None
}


# ============================================================
# HELPER: SIMULATION TIME
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
# HELPER: AI INTERVAL
# ============================================================

def get_ai_interval_key(
    month,
    day,
    hour
):

    day_of_year = date(
        2013,
        month,
        day
    ).timetuple().tm_yday

    absolute_hour = (
        (day_of_year - 1) * 24
        + hour
    )

    return (
        absolute_hour
        // controller_state[
            "ai_interval_hours"
        ]
    )


# ============================================================
# HELPER: SAFE METER HANDLE
# ============================================================

def safe_get_meter_handle(
    state_argument,
    meter_name
):

    try:

        handle = (
            api.exchange.get_meter_handle(
                state_argument,
                meter_name
            )
        )

        if handle == -1:

            print(
                f"[METER WARNING] "
                f"{meter_name} not available."
            )

        else:

            print(
                f"[METER OK] "
                f"{meter_name}: {handle}"
            )

        return handle

    except Exception as error:

        print(
            f"[METER ERROR] "
            f"{meter_name}: {error}"
        )

        return -1


# ============================================================
# HELPER: SAFE METER READ
# ============================================================

def read_meter_value(
    state_argument,
    handle
):

    if handle is None or handle == -1:
        return 0.0

    try:

        value = (
            api.exchange.get_meter_value(
                state_argument,
                handle
            )
        )

        return float(
            value or 0.0
        )

    except Exception:
        return 0.0


# ============================================================
# HELPER: JOULES -> KWH
# ============================================================

def joules_to_kwh(value):

    return max(
        0.0,
        float(value or 0.0)
        * JOULES_TO_KWH
    )


def read_meter_kwh(
    state_argument,
    handle
):

    return joules_to_kwh(

        read_meter_value(
            state_argument,
            handle
        )
    )


# ============================================================
# READ ENERGY STATE
# ============================================================

def read_energy_state(
    state_argument
):

    hvac_electricity_kwh = (
        read_meter_kwh(
            state_argument,
            handles["electricity_hvac"]
        )
    )

    cooling_electricity_kwh = (
        read_meter_kwh(
            state_argument,
            handles["cooling_electricity"]
        )
    )

    heating_natural_gas_kwh = (
        read_meter_kwh(
            state_argument,
            handles["heating_natural_gas"]
        )
    )

    fans_electricity_kwh = (
        read_meter_kwh(
            state_argument,
            handles["fans_electricity"]
        )
    )

    pumps_electricity_kwh = (
        read_meter_kwh(
            state_argument,
            handles["pumps_electricity"]
        )
    )

    heating_demand_kwh = (
        read_meter_kwh(
            state_argument,
            handles["heating_demand"]
        )
    )

    cooling_demand_kwh = (
        read_meter_kwh(
            state_argument,
            handles["cooling_demand"]
        )
    )

    # IMPORTANT:
    # Electricity:HVAC already includes electrical HVAC loads.
    # Natural gas is added separately.
    total_hvac_site_energy_kwh = (
        hvac_electricity_kwh
        + heating_natural_gas_kwh
    )

    return {

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

        "heating_natural_gas_kwh":
            round(
                heating_natural_gas_kwh,
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
            )
    }


# ============================================================
# CARBON CALCULATION
# ============================================================

def calculate_hvac_carbon(
    energy_state,
    grid_carbon_intensity
):

    electricity_carbon_kg = (

        float(
            energy_state[
                "hvac_electricity_kwh"
            ]
        )

        * float(
            grid_carbon_intensity
        )
    )

    gas_carbon_kg = (

        float(
            energy_state[
                "heating_natural_gas_kwh"
            ]
        )

        * NATURAL_GAS_CARBON_FACTOR
    )

    total_hvac_carbon_kg = (
        electricity_carbon_kg
        + gas_carbon_kg
    )

    return {

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
            )
    }


# ============================================================
# REAL-TIME COMFORT GUARD
# ============================================================

def apply_realtime_comfort_guard(
    heating,
    cooling,
    occupancy,
    min_temp,
    max_temp
):
    """
    Fast deterministic comfort protection.

    Runs every EnergyPlus control timestep.

    The Qwen LLM remains supervisory and runs every
    six simulated hours.

    This guard responds immediately to occupied-zone
    temperature violations.
    """

    heating = float(
        heating
    )

    cooling = float(
        cooling
    )

    occupancy = float(
        occupancy or 0.0
    )

    corrections = []


    # ========================================================
    # UNOCCUPIED
    # ========================================================

    if occupancy <= 0:

        return (
            round(heating, 2),
            round(cooling, 2),
            corrections
        )


    # ========================================================
    # OCCUPIED BASE LIMITS
    # ========================================================

    heating = max(
        heating,
        20.0
    )

    cooling = min(
        cooling,
        26.0
    )


    # ========================================================
    # HEATING RECOVERY
    # ========================================================

    if min_temp is not None:

        min_temp = float(
            min_temp
        )

        # Emergency cold condition.
        if min_temp < 18.5:

            if heating < 22.0:

                heating = 22.0

                corrections.append(
                    "Emergency heating recovery "
                    "because occupied temperature "
                    "fell below 18.5 C."
                )

        # Strong recovery.
        elif min_temp < 19.0:

            if heating < 21.5:

                heating = 21.5

                corrections.append(
                    "Strong heating recovery "
                    "because occupied temperature "
                    "fell below 19 C."
                )

        # Normal comfort recovery.
        elif min_temp < 20.0:

            if heating < 21.0:

                heating = 21.0

                corrections.append(
                    "Heating comfort recovery "
                    "because occupied temperature "
                    "fell below 20 C."
                )

        # Preventive action near boundary.
        elif min_temp < 20.5:

            if heating < 20.0:

                heating = 20.0

                corrections.append(
                    "Heating maintained at occupied "
                    "comfort minimum."
                )


    # ========================================================
    # COOLING RECOVERY
    # ========================================================

    if max_temp is not None:

        max_temp = float(
            max_temp
        )

        # Emergency hot condition.
        if max_temp > 27.5:

            if cooling > 23.5:

                cooling = 23.5

                corrections.append(
                    "Emergency cooling recovery "
                    "because occupied temperature "
                    "exceeded 27.5 C."
                )

        # Strong cooling.
        elif max_temp > 27.0:

            if cooling > 24.0:

                cooling = 24.0

                corrections.append(
                    "Strong cooling recovery "
                    "because occupied temperature "
                    "exceeded 27 C."
                )

        # Normal comfort recovery.
        elif max_temp > 26.0:

            if cooling > 25.0:

                cooling = 25.0

                corrections.append(
                    "Cooling comfort recovery "
                    "because occupied temperature "
                    "exceeded 26 C."
                )

        # Preventive action.
        elif max_temp > 25.5:

            if cooling > 25.5:

                cooling = 25.5

                corrections.append(
                    "Preventive cooling near "
                    "upper comfort boundary."
                )


    # ========================================================
    # PHYSICAL LIMITS
    # ========================================================

    heating = max(
        16.0,
        min(
            22.0,
            heating
        )
    )

    cooling = max(
        23.0,
        min(
            30.0,
            cooling
        )
    )


    # ========================================================
    # MINIMUM DEADBAND
    # ========================================================

    if cooling - heating < 2.0:

        proposed_cooling = (
            heating + 2.0
        )

        if proposed_cooling <= 30.0:

            cooling = (
                proposed_cooling
            )

        else:

            heating = (
                cooling - 2.0
            )

        corrections.append(
            "Real-time guard enforced "
            "minimum 2 C thermostat deadband."
        )


    return (
        round(
            heating,
            2
        ),

        round(
            cooling,
            2
        ),

        corrections
    )


# ============================================================
# MAIN CONTROL CALLBACK
# ============================================================

def control_callback(
    state_argument
):

    # ========================================================
    # WAIT FOR ENERGYPLUS API
    # ========================================================

    if not api.exchange.api_data_fully_ready(
        state_argument
    ):
        return


    # ========================================================
    # INITIALIZE HANDLES
    # ========================================================

    if not handles[
        "initialized"
    ]:

        print(
            "\nInitializing AI controller handles..."
        )


        # ----------------------------------------------------
        # HVAC ACTUATORS
        # ----------------------------------------------------

        handles[
            "heating_actuator"
        ] = (

            api.exchange.get_actuator_handle(

                state_argument,

                "Schedule:Compact",

                "Schedule Value",

                "HTG-SETP-SCH"
            )
        )


        handles[
            "cooling_actuator"
        ] = (

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

        handles[
            "outdoor_temp"
        ] = (

            api.exchange.get_variable_handle(

                state_argument,

                "Site Outdoor Air Drybulb Temperature",

                "Environment"
            )
        )


        # ----------------------------------------------------
        # ZONE HANDLES
        # ----------------------------------------------------

        handles[
            "zone_temps"
        ] = []

        handles[
            "occupancies"
        ] = []


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


        # ====================================================
        # ENERGY METERS
        # ====================================================

        meter_names = {

            "electricity_hvac":
                "Electricity:HVAC",

            "cooling_electricity":
                "Cooling:Electricity",

            "heating_natural_gas":
                "Heating:NaturalGas",

            "fans_electricity":
                "Fans:Electricity",

            "pumps_electricity":
                "Pumps:Electricity",

            "heating_demand":
                "PlantLoopHeatingDemand:HVAC",

            "cooling_demand":
                "PlantLoopCoolingDemand:HVAC"
        }


        for (
            key,
            meter_name
        ) in meter_names.items():

            handles[
                key
            ] = safe_get_meter_handle(

                state_argument,

                meter_name
            )


        # ----------------------------------------------------
        # DEBUG
        # ----------------------------------------------------

        print(
            "\nHeating actuator:",
            handles[
                "heating_actuator"
            ]
        )

        print(
            "Cooling actuator:",
            handles[
                "cooling_actuator"
            ]
        )

        print(
            "Outdoor temperature:",
            handles[
                "outdoor_temp"
            ]
        )

        print(
            "Zone temperatures:",
            handles[
                "zone_temps"
            ]
        )

        print(
            "Occupancies:",
            handles[
                "occupancies"
            ]
        )


        # ----------------------------------------------------
        # VALIDATE REQUIRED HANDLES
        # ----------------------------------------------------

        required_handles = (

            [
                handles[
                    "heating_actuator"
                ],

                handles[
                    "cooling_actuator"
                ],

                handles[
                    "outdoor_temp"
                ]
            ]

            + handles[
                "zone_temps"
            ]

            + handles[
                "occupancies"
            ]
        )


        if any(
            handle == -1
            for handle
            in required_handles
        ):

            print(
                "\nERROR: One or more required "
                "EnergyPlus handles are invalid."
            )

            return


        handles[
            "initialized"
        ] = True


        print(
            "\nAll AI controller handles initialized."
        )


    # ========================================================
    # IGNORE WARMUP
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

            handles[
                "outdoor_temp"
            ]
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
        in handles[
            "zone_temps"
        ]
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
        in handles[
            "occupancies"
        ]
    ]


    total_occupancy = sum(
        occupancies
    )


    # ========================================================
    # OCCUPIED TEMPERATURE STATISTICS
    # ========================================================

    occupied_temperatures = [

        temperature

        for (
            temperature,
            occupancy
        )

        in zip(
            zone_temperatures,
            occupancies
        )

        if occupancy > 0
    ]


    if occupied_temperatures:

        avg_occupied_temperature = (

            sum(
                occupied_temperatures
            )

            / len(
                occupied_temperatures
            )
        )


        min_occupied_temperature = min(
            occupied_temperatures
        )


        max_occupied_temperature = max(
            occupied_temperatures
        )


    else:

        avg_occupied_temperature = None

        min_occupied_temperature = None

        max_occupied_temperature = None


    # ========================================================
    # ENERGY METER READINGS
    # ========================================================

    energy_state = (
        read_energy_state(
            state_argument
        )
    )


    hvac_energy_kwh = (

        energy_state[
            "hvac_electricity_kwh"
        ]
    )


    # ========================================================
    # HVAC POWER
    # ========================================================

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

            hvac_energy_kwh

            / timestep_hours
        )

    else:

        hvac_power_kw = 0.0


    hvac_power_kw = round(
        hvac_power_kw,
        4
    )


    # ========================================================
    # SIMULATION DATE / TIME
    # ========================================================

    simulation_time = (
        get_simulation_time(
            state_argument
        )
    )


    month = (
        api.exchange.month(
            state_argument
        )
    )


    day = (
        api.exchange.day_of_month(
            state_argument
        )
    )


    hour = (
        api.exchange.hour(
            state_argument
        )
    )


    # ========================================================
    # DYNAMIC GRID CARBON SIGNAL
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


        carbon_intensity = 0.42

        carbon_level = (
            "moderate"
        )


    carbon_intensity = round(
        carbon_intensity,
        4
    )


    # ========================================================
    # CURRENT TIMESTEP CARBON
    # ========================================================

    carbon_state = (

        calculate_hvac_carbon(

            energy_state,

            carbon_intensity
        )
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

        "zones": [

            {

                "name":
                    zone,

                "temperature":
                    round(
                        float(
                            temperature
                        ),
                        2
                    ),

                "occupancy":
                    round(
                        float(
                            occupancy
                        ),
                        2
                    )
            }

            for (
                zone,
                temperature,
                occupancy
            )

            in zip(
                ZONES,
                zone_temperatures,
                occupancies
            )
        ],

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
                    avg_occupied_temperature
                ),
                2
            )

            if avg_occupied_temperature
            is not None

            else None
        ),

        "min_occupied_temperature": (

            round(
                float(
                    min_occupied_temperature
                ),
                2
            )

            if min_occupied_temperature
            is not None

            else None
        ),

        "max_occupied_temperature": (

            round(
                float(
                    max_occupied_temperature
                ),
                2
            )

            if max_occupied_temperature
            is not None

            else None
        ),

        "current_setpoints": {

            "heating":
                controller_state[
                    "heating"
                ],

            "cooling":
                controller_state[
                    "cooling"
                ]
        },

        # ----------------------------------------------------
        # ENERGY
        # ----------------------------------------------------

        "hvac_power_kw":
            hvac_power_kw,

        "hvac_energy_kwh":
            energy_state[
                "hvac_electricity_kwh"
            ],

        "hvac_electricity_kwh":
            energy_state[
                "hvac_electricity_kwh"
            ],

        "cooling_electricity_kwh":
            energy_state[
                "cooling_electricity_kwh"
            ],

        "heating_natural_gas_kwh":
            energy_state[
                "heating_natural_gas_kwh"
            ],

        "fans_electricity_kwh":
            energy_state[
                "fans_electricity_kwh"
            ],

        "pumps_electricity_kwh":
            energy_state[
                "pumps_electricity_kwh"
            ],

        "heating_demand_kwh":
            energy_state[
                "heating_demand_kwh"
            ],

        "cooling_demand_kwh":
            energy_state[
                "cooling_demand_kwh"
            ],

        "total_hvac_site_energy_kwh":
            energy_state[
                "total_hvac_site_energy_kwh"
            ],

        # ----------------------------------------------------
        # CARBON
        # ----------------------------------------------------

        "carbon_intensity":
            carbon_intensity,

        "carbon_level":
            carbon_level,

        "hvac_carbon_kg":
            carbon_state[
                "total_hvac_carbon_kg"
            ],

        "electricity_carbon_kg":
            carbon_state[
                "electricity_carbon_kg"
            ],

        "gas_carbon_kg":
            carbon_state[
                "gas_carbon_kg"
            ],

        "total_hvac_carbon_kg":
            carbon_state[
                "total_hvac_carbon_kg"
            ]
    }


    # ========================================================
    # AI INTERVAL
    # ========================================================

    ai_interval_key = (

        get_ai_interval_key(
            month,
            day,
            hour
        )
    )


    # ========================================================
    # OPERATIONAL METRICS
    # ========================================================

    metrics_hour_key = (
        month,
        day,
        hour
    )


    if (
        controller_state[
            "last_metrics_hour"
        ]

        != metrics_hour_key
    ):

        try:

            log_operational_metrics(

                simulation_time=
                    simulation_time,

                building_state=
                    building_state,

                heating_setpoint=
                    controller_state[
                        "heating"
                    ],

                cooling_setpoint=
                    controller_state[
                        "cooling"
                    ],

                timestep_hours=
                    timestep_hours
            )


            controller_state[
                "last_metrics_hour"
            ] = metrics_hour_key


        except Exception as metrics_error:

            print(
                "\nWARNING: Operational metrics "
                "logging failed:",
                metrics_error
            )


    # ========================================================
    # SHOULD LLM RUN?
    # ========================================================

    should_call_ai = (

        controller_state[
            "last_ai_interval"
        ]

        != ai_interval_key
    )


    # ========================================================
    # AI SUPERVISORY CONTROL
    # ========================================================

    if should_call_ai:

        controller_state[
            "last_ai_interval"
        ] = ai_interval_key


        controller_state[
            "ai_calls"
        ] += 1


        print(
            "\n----------------------------------------"
        )

        print(
            "[AI CONTROL]",
            simulation_time
        )

        print(
            "AI call:",
            controller_state[
                "ai_calls"
            ]
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
            "HVAC power:",
            hvac_power_kw,
            "kW"
        )


        print(
            "\n[ENERGY DIAGNOSTICS]"
        )

        print(
            "HVAC electricity:",
            energy_state[
                "hvac_electricity_kwh"
            ],
            "kWh"
        )

        print(
            "Cooling electricity:",
            energy_state[
                "cooling_electricity_kwh"
            ],
            "kWh"
        )

        print(
            "Heating natural gas:",
            energy_state[
                "heating_natural_gas_kwh"
            ],
            "kWh"
        )

        print(
            "Fan electricity:",
            energy_state[
                "fans_electricity_kwh"
            ],
            "kWh"
        )

        print(
            "Pump electricity:",
            energy_state[
                "pumps_electricity_kwh"
            ],
            "kWh"
        )

        print(
            "Heating demand:",
            energy_state[
                "heating_demand_kwh"
            ],
            "kWh"
        )

        print(
            "Cooling demand:",
            energy_state[
                "cooling_demand_kwh"
            ],
            "kWh"
        )

        print(
            "Total HVAC site energy:",
            energy_state[
                "total_hvac_site_energy_kwh"
            ],
            "kWh"
        )

        print(
            "Electricity carbon:",
            carbon_state[
                "electricity_carbon_kg"
            ],
            "kg CO2"
        )

        print(
            "Gas carbon:",
            carbon_state[
                "gas_carbon_kg"
            ],
            "kg CO2"
        )

        print(
            "Total HVAC carbon:",
            carbon_state[
                "total_hvac_carbon_kg"
            ],
            "kg CO2"
        )

        print(
            "Current:",
            controller_state[
                "heating"
            ],
            "/",
            controller_state[
                "cooling"
            ]
        )


        # ====================================================
        # GET SAFE AI DECISION
        # ====================================================

        try:

            safe_action = (

                get_safe_ai_action(
                    building_state
                )
            )


            controller_state[
                "last_safe_action"
            ] = safe_action


            # ------------------------------------------------
            # RAW LLM DECISION
            # ------------------------------------------------

            raw_llm_decision = (

                safe_action.get(
                    "raw_llm_decision",
                    {}
                )

                or {}
            )


            # ------------------------------------------------
            # APPROVED SETPOINTS
            # ------------------------------------------------

            new_heating = float(

                safe_action[
                    "heating_setpoint"
                ]
            )


            new_cooling = float(

                safe_action[
                    "cooling_setpoint"
                ]
            )


            # ------------------------------------------------
            # AI METRICS
            # ------------------------------------------------

            try:

                log_ai_metrics(

                    simulation_time=
                        simulation_time,

                    building_state=
                        building_state,

                    safe_action=
                        safe_action,

                    ai_call_number=
                        controller_state[
                            "ai_calls"
                        ]
                )


            except Exception as metrics_error:

                print(
                    "\nWARNING: AI metrics "
                    "logging failed:",
                    metrics_error
                )


            # ------------------------------------------------
            # UPDATE CONTROLLER
            # ------------------------------------------------

            controller_state[
                "heating"
            ] = new_heating


            controller_state[
                "cooling"
            ] = new_cooling


            # ------------------------------------------------
            # INTERVENTION STATISTICS
            # ------------------------------------------------

            if safe_action.get(
                "modified",
                False
            ):

                controller_state[
                    "safety_interventions"
                ] += 1


            if safe_action.get(
                "semantic_modified",
                False
            ):

                controller_state[
                    "semantic_interventions"
                ] += 1


            # ------------------------------------------------
            # LIVE AI DECISION
            # ------------------------------------------------

            try:

                write_live_ai_decision(

                    simulation_time=
                        simulation_time,

                    building_state=
                        building_state,

                    raw_decision=
                        raw_llm_decision,

                    safe_action=
                        safe_action,

                    ai_call_number=
                        controller_state[
                            "ai_calls"
                        ]
                )


            except Exception as bridge_error:

                print(
                    "WARNING: Live AI decision "
                    "write failed:",
                    bridge_error
                )


            # ------------------------------------------------
            # CONSOLE REPORT
            # ------------------------------------------------

            print(
                "AI approved:",
                new_heating,
                "/",
                new_cooling
            )


            if raw_llm_decision:

                print(
                    "LLM proposed:",
                    raw_llm_decision.get(
                        "heating",
                        "?"
                    ),
                    "/",
                    raw_llm_decision.get(
                        "cooling",
                        "?"
                    )
                )


            print(
                "Reason:",
                safe_action.get(
                    "ai_reason",
                    ""
                )
            )


            print(
                "Energy strategy:",
                safe_action.get(
                    "energy_strategy",
                    ""
                )
            )


            print(
                "Comfort risk:",
                safe_action.get(
                    "comfort_risk",
                    "unknown"
                )
            )


            if safe_action.get(
                "semantic_corrections"
            ):

                print(
                    "Semantic corrections:"
                )

                for correction in (

                    safe_action[
                        "semantic_corrections"
                    ]
                ):

                    print(
                        "  -",
                        correction
                    )


            if safe_action.get(
                "reasons"
            ):

                print(
                    "Safety corrections:"
                )

                for reason in (

                    safe_action[
                        "reasons"
                    ]
                ):

                    print(
                        "  -",
                        reason
                    )


        # ====================================================
        # FAIL SAFE
        # ====================================================

        except Exception as error:

            controller_state[
                "ai_failures"
            ] += 1


            print(
                "\nWARNING: AI controller failed:"
            )

            print(
                error
            )

            print(
                "Retaining previous safe setpoints:",
                controller_state[
                    "heating"
                ],
                "/",
                controller_state[
                    "cooling"
                ]
            )


    # ========================================================
    # REAL-TIME COMFORT PROTECTION
    # ========================================================

    (
        guarded_heating,
        guarded_cooling,
        comfort_corrections

    ) = apply_realtime_comfort_guard(

        heating=
            controller_state[
                "heating"
            ],

        cooling=
            controller_state[
                "cooling"
            ],

        occupancy=
            total_occupancy,

        min_temp=
            min_occupied_temperature,

        max_temp=
            max_occupied_temperature
    )


    # Detect actual change.
    comfort_guard_changed = (

        abs(
            guarded_heating
            - controller_state[
                "heating"
            ]
        ) > 0.001

        or

        abs(
            guarded_cooling
            - controller_state[
                "cooling"
            ]
        ) > 0.001
    )


    if comfort_guard_changed:

        controller_state[
            "comfort_guard_interventions"
        ] += 1


    controller_state[
        "heating"
    ] = guarded_heating


    controller_state[
        "cooling"
    ] = guarded_cooling


    if comfort_corrections:

        print(
            "\n[REAL-TIME COMFORT GUARD]",
            simulation_time
        )

        print(
            "Occupancy:",
            round(
                total_occupancy,
                2
            )
        )

        print(
            "Occupied temperature range:",
            min_occupied_temperature,
            "-",
            max_occupied_temperature
        )

        print(
            "Protected setpoints:",
            guarded_heating,
            "/",
            guarded_cooling
        )

        for correction in (
            comfort_corrections
        ):

            print(
                "  -",
                correction
            )


    # ========================================================
    # APPLY APPROVED HVAC ACTION
    # ========================================================

    api.exchange.set_actuator_value(

        state_argument,

        handles[
            "heating_actuator"
        ],

        controller_state[
            "heating"
        ]
    )


    api.exchange.set_actuator_value(

        state_argument,

        handles[
            "cooling_actuator"
        ],

        controller_state[
            "cooling"
        ]
    )


    # ========================================================
    # LIVE BUILDING STATE
    # ========================================================

    try:

        write_building_state(

            simulation_time=
                simulation_time,

            outdoor_temperature=
                outdoor_temperature,

            zone_temperatures=
                zone_temperatures,

            occupancies=
                occupancies,

            heating_setpoint=
                controller_state[
                    "heating"
                ],

            cooling_setpoint=
                controller_state[
                    "cooling"
                ],

            hvac_power_kw=
                hvac_power_kw,

            carbon_intensity=
                carbon_intensity
        )


    except Exception as error:

        print(
            "WARNING: Live state "
            "write failed:",
            error
        )


# ============================================================
# REGISTER CALLBACK
# ============================================================

api.runtime.callback_begin_zone_timestep_after_init_heat_balance(
    state,
    control_callback
)


# ============================================================
# ENERGYPLUS ARGUMENTS
# ============================================================

arguments = [

    "-r",

    "-w",
    str(
        WEATHER
    ),

    "-d",
    str(
        OUTPUT
    ),

    str(
        MODEL
    )
]


# ============================================================
# RUN INFORMATION
# ============================================================

print(
    "\n=============================================="
)

print(
    "       AUTONOMOUS AI-BMS CONTROL RUN"
)

print(
    "=============================================="
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
    "\nController      : Local Qwen LLM"
)

print(
    "Semantic Guard  : ENABLED"
)

print(
    "Safety Guard    : ENABLED"
)

print(
    "Real-time Guard : ENABLED"
)

print(
    "Fail-safe       : ENABLED"
)

print(
    "Carbon-aware    : ENABLED"
)

print(
    "Dynamic Carbon  : ENABLED"
)

print(
    "Energy Metering : ELECTRIC + NATURAL GAS"
)

print(
    "Live State      : ENABLED"
)

print(
    "AI Decision Feed: ENABLED"
)

print(
    "AI Metrics      : ENABLED"
)

print(
    "Operational Data: ENABLED"
)

print(
    "AI interval     :",
    controller_state[
        "ai_interval_hours"
    ],
    "simulated hours"
)

print(
    "Comfort guard   : EVERY ENERGYPLUS TIMESTEP"
)

print(
    "\nStarting EnergyPlus simulation...\n"
)


# ============================================================
# INITIALIZE EVALUATION FILES
# ============================================================

initialize_metrics_file()

initialize_operational_metrics()


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
    "\n=============================================="
)


if exit_code == 0:

    print(
        "AI-controlled simulation "
        "completed successfully."
    )

else:

    print(
        "AI-controlled simulation FAILED."
    )

    print(
        "Exit code:",
        exit_code
    )


print(
    "\nAI calls:",
    controller_state[
        "ai_calls"
    ]
)

print(
    "AI failures:",
    controller_state[
        "ai_failures"
    ]
)

print(
    "Safety interventions:",
    controller_state[
        "safety_interventions"
    ]
)

print(
    "Semantic interventions:",
    controller_state[
        "semantic_interventions"
    ]
)

print(
    "Real-time comfort interventions:",
    controller_state[
        "comfort_guard_interventions"
    ]
)

print(
    "Final heating setpoint:",
    controller_state[
        "heating"
    ]
)

print(
    "Final cooling setpoint:",
    controller_state[
        "cooling"
    ]
)
print(
    "Comfort guard interventions:",
    controller_state[
        "comfort_guard_interventions"
    ]
)

print(
    "=============================================="
)