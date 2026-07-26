import sys
from pathlib import Path

# Allow imports from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# EnergyPlus
ENERGYPLUS_DIR = r"C:\EnergyPlusV26-1-0"

if ENERGYPLUS_DIR not in sys.path:
    sys.path.insert(0, ENERGYPLUS_DIR)

from pyenergyplus.api import EnergyPlusAPI
from controller.safety_guard import SafetyGuard


# ============================================================
# PATHS
# ============================================================

MODEL = Path(
    r"building\models\5ZoneAI.idf"
).resolve()

WEATHER = Path(
    r"building\weather\chicago.epw"
).resolve()

OUTPUT = Path(
    r"results\rule_v3"
).resolve()

OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# ENERGYPLUS
# ============================================================

api = EnergyPlusAPI()
state = api.state_manager.new_state()


ZONES = [
    "SPACE1-1",
    "SPACE2-1",
    "SPACE3-1",
    "SPACE4-1",
    "SPACE5-1"
]


handles = {
    "initialized": False,

    "heating_actuator": -1,
    "cooling_actuator": -1,

    "outdoor_temp": -1,

    "zone_temps": [],
    "occupancies": []
}


# Keep track of previous approved values
controller_state = {
    "heating": 20.0,
    "cooling": 25.0
}


# ============================================================
# CONTROLLER
# ============================================================

def control_callback(state_argument):

    if not api.exchange.api_data_fully_ready(
        state_argument
    ):
        return


    # ========================================================
    # INITIALIZE
    # ========================================================

    if not handles["initialized"]:

        print("\nInitializing dual-controller handles...")


        handles["heating_actuator"] = (
            api.exchange.get_actuator_handle(
                state_argument,
                "Schedule:Compact",
                "Schedule Value",
                "HTG-SETP-SCH"
            )
        )


        handles["cooling_actuator"] = (
            api.exchange.get_actuator_handle(
                state_argument,
                "Schedule:Compact",
                "Schedule Value",
                "CLG-SETP-SCH"
            )
        )


        handles["outdoor_temp"] = (
            api.exchange.get_variable_handle(
                state_argument,
                "Site Outdoor Air Drybulb Temperature",
                "Environment"
            )
        )


        for zone in ZONES:

            temp_handle = (
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

            handles["zone_temps"].append(
                temp_handle
            )

            handles["occupancies"].append(
                occupancy_handle
            )


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


        all_handles = (
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
            for handle in all_handles
        ):

            print(
                "\nERROR: Invalid EnergyPlus handle detected."
            )

            return


        handles["initialized"] = True

        print(
            "\nAll dual-controller handles initialized."
        )


    # ========================================================
    # READ BUILDING STATE
    # ========================================================

    outdoor_temp = (
        api.exchange.get_variable_value(
            state_argument,
            handles["outdoor_temp"]
        )
    )


    zone_temperatures = [

        api.exchange.get_variable_value(
            state_argument,
            handle
        )

        for handle in handles["zone_temps"]
    ]


    occupancies = [

        api.exchange.get_variable_value(
            state_argument,
            handle
        )

        for handle in handles["occupancies"]
    ]


    total_occupancy = sum(
        occupancies
    )


    occupied_temperatures = [

        temperature

        for temperature, occupancy
        in zip(
            zone_temperatures,
            occupancies
        )

        if occupancy > 0
    ]


    # ========================================================
    # PROPOSE SETPOINTS
    # ========================================================

    if total_occupancy <= 0:

        # Wide deadband when building is empty
        proposed_heating = 18.0
        proposed_cooling = 29.0


    else:

        max_temp = max(
            occupied_temperatures
        )

        min_temp = min(
            occupied_temperatures
        )

        avg_temp = (
            sum(occupied_temperatures)
            / len(occupied_temperatures)
        )


        # ----------------------------------------------------
        # Heating decision
        # ----------------------------------------------------

        if min_temp < 20.0:

            proposed_heating = 21.0

        elif avg_temp < 21.5:

            proposed_heating = 20.5

        else:

            proposed_heating = 19.0


        # ----------------------------------------------------
        # Cooling decision
        # ----------------------------------------------------

        if max_temp >= 26.0:

            proposed_cooling = 23.5

        elif max_temp >= 25.0:

            proposed_cooling = 24.5

        elif avg_temp < 23.5:

            proposed_cooling = 26.0

        elif total_occupancy < 15:

            proposed_cooling = 25.5

        elif outdoor_temp < 20.0:

            proposed_cooling = 25.5

        else:

            proposed_cooling = 25.0


    # ========================================================
    # SAFETY GUARD
    # ========================================================

    safe_action = SafetyGuard.validate(

        proposed_heating=proposed_heating,
        proposed_cooling=proposed_cooling,

        current_heating=controller_state[
            "heating"
        ],

        current_cooling=controller_state[
            "cooling"
        ]
    )


    heating_setpoint = (
        safe_action["heating_setpoint"]
    )

    cooling_setpoint = (
        safe_action["cooling_setpoint"]
    )


    # Save approved state
    controller_state["heating"] = (
        heating_setpoint
    )

    controller_state["cooling"] = (
        cooling_setpoint
    )


    # ========================================================
    # APPLY TO ENERGYPLUS
    # ========================================================

    api.exchange.set_actuator_value(
        state_argument,
        handles["heating_actuator"],
        heating_setpoint
    )


    api.exchange.set_actuator_value(
        state_argument,
        handles["cooling_actuator"],
        cooling_setpoint
    )


# ============================================================
# CALLBACK
# ============================================================

api.runtime.callback_begin_zone_timestep_after_init_heat_balance(
    state,
    control_callback
)


# ============================================================
# RUN
# ============================================================

arguments = [
    "-r",
    "-w",
    str(WEATHER),
    "-d",
    str(OUTPUT),
    str(MODEL)
]


print("\n========================================")
print("       AI-BMS DUAL CONTROLLER V3")
print("========================================")

print("\nHeating control : ENABLED")
print("Cooling control : ENABLED")
print("Safety Guard    : ENABLED")

print("\nStarting simulation...\n")


exit_code = api.runtime.run_energyplus(
    state,
    arguments
)


print("\n========================================")

if exit_code == 0:

    print(
        "Dual-controller simulation completed successfully."
    )

else:

    print(
        f"Simulation failed. Exit code: {exit_code}"
    )

print("========================================")