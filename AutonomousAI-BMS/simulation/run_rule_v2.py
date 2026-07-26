import sys
from pathlib import Path

# ============================================================
# ENERGYPLUS PYTHON API
# ============================================================

ENERGYPLUS_DIR = r"C:\EnergyPlusV26-1-0"

if ENERGYPLUS_DIR not in sys.path:
    sys.path.insert(0, ENERGYPLUS_DIR)

from pyenergyplus.api import EnergyPlusAPI


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
    r"results\rule_v2"
).resolve()

OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# ENERGYPLUS API
# ============================================================

api = EnergyPlusAPI()

state = api.state_manager.new_state()


# ============================================================
# ZONES
# ============================================================

ZONES = [
    "SPACE1-1",
    "SPACE2-1",
    "SPACE3-1",
    "SPACE4-1",
    "SPACE5-1"
]


# ============================================================
# HANDLES
# ============================================================

handles = {
    "initialized": False,
    "cooling_actuator": -1,
    "outdoor_temp": -1,
    "zone_temps": [],
    "occupancies": []
}


# ============================================================
# CONTROLLER CALLBACK
# ============================================================

def control_callback(state_argument):

    # --------------------------------------------------------
    # Wait until EnergyPlus data is ready
    # --------------------------------------------------------

    if not api.exchange.api_data_fully_ready(
        state_argument
    ):
        return


    # --------------------------------------------------------
    # INITIALIZE HANDLES ONCE
    # --------------------------------------------------------

    if not handles["initialized"]:

        print("\nInitializing EnergyPlus handles...")

        # Cooling setpoint actuator
        handles["cooling_actuator"] = (
            api.exchange.get_actuator_handle(
                state_argument,
                "Schedule:Compact",
                "Schedule Value",
                "CLG-SETP-SCH"
            )
        )

        # Outdoor temperature
        handles["outdoor_temp"] = (
            api.exchange.get_variable_handle(
                state_argument,
                "Site Outdoor Air Drybulb Temperature",
                "Environment"
            )
        )

        # Zone variables
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
            "Cooling actuator:",
            handles["cooling_actuator"]
        )

        print(
            "Outdoor temperature handle:",
            handles["outdoor_temp"]
        )

        print(
            "Zone temperature handles:",
            handles["zone_temps"]
        )

        print(
            "Occupancy handles:",
            handles["occupancies"]
        )


        # ----------------------------------------------------
        # Validate handles
        # ----------------------------------------------------

        all_handles = (
            [handles["cooling_actuator"]]
            + [handles["outdoor_temp"]]
            + handles["zone_temps"]
            + handles["occupancies"]
        )

        if any(
            handle == -1
            for handle in all_handles
        ):

            print(
                "\nERROR: One or more EnergyPlus "
                "handles could not be found."
            )

            return


        handles["initialized"] = True

        print(
            "All EnergyPlus handles initialized successfully.\n"
        )


    # ========================================================
    # READ CURRENT BUILDING STATE
    # ========================================================

    outdoor_temp = (
        api.exchange.get_variable_value(
            state_argument,
            handles["outdoor_temp"]
        )
    )


    # --------------------------------------------------------
    # Zone temperatures
    # --------------------------------------------------------

    zone_temperatures = []

    for handle in handles["zone_temps"]:

        temperature = (
            api.exchange.get_variable_value(
                state_argument,
                handle
            )
        )

        zone_temperatures.append(
            temperature
        )


    # --------------------------------------------------------
    # Occupancy
    # --------------------------------------------------------

    occupancies = []

    for handle in handles["occupancies"]:

        occupancy = (
            api.exchange.get_variable_value(
                state_argument,
                handle
            )
        )

        occupancies.append(
            occupancy
        )


    total_occupancy = sum(
        occupancies
    )


    # ========================================================
    # OCCUPANCY-AWARE TEMPERATURE
    # ========================================================

    occupied_temperatures = []

    for temp, occupancy in zip(
        zone_temperatures,
        occupancies
    ):

        if occupancy > 0:

            occupied_temperatures.append(
                temp
            )


    if occupied_temperatures:

        max_occupied_temp = max(
            occupied_temperatures
        )

        avg_occupied_temp = (
            sum(occupied_temperatures)
            / len(occupied_temperatures)
        )

    else:

        max_occupied_temp = None
        avg_occupied_temp = None


    # ========================================================
    # RULE-BASED CONTROLLER V2
    # ========================================================

    if total_occupancy <= 0:

        # Empty building
        cooling_setpoint = 29.0


    elif max_occupied_temp >= 26.0:

        # At least one occupied zone is getting too warm
        cooling_setpoint = 23.0


    elif max_occupied_temp >= 25.0:

        cooling_setpoint = 24.0


    elif avg_occupied_temp < 23.5:

        # Occupied areas are already cool
        cooling_setpoint = 26.0


    elif total_occupancy < 15:

        # Low occupancy
        cooling_setpoint = 25.5


    elif outdoor_temp < 20.0:

        # Mild/cool outdoor conditions
        cooling_setpoint = 25.5


    else:

        cooling_setpoint = 25.0


    # ========================================================
    # SAFETY BOUNDS
    # ========================================================

    cooling_setpoint = max(
        22.0,
        min(
            cooling_setpoint,
            29.0
        )
    )


    # ========================================================
    # APPLY ACTION TO ENERGYPLUS
    # ========================================================

    api.exchange.set_actuator_value(
        state_argument,
        handles["cooling_actuator"],
        cooling_setpoint
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
    str(WEATHER),
    "-d",
    str(OUTPUT),
    str(MODEL)
]


# ============================================================
# RUN
# ============================================================

print("\n====================================")
print("      AI-BMS RULE CONTROLLER V2")
print("====================================")

print("\nModel:")
print(MODEL)

print("\nWeather:")
print(WEATHER)

print("\nOutput:")
print(OUTPUT)

print("\nStarting controlled simulation...\n")


exit_code = api.runtime.run_energyplus(
    state,
    arguments
)


print("\n====================================")

if exit_code == 0:

    print(
        "Rule V2 simulation completed successfully."
    )

else:

    print(
        f"EnergyPlus failed with exit code {exit_code}"
    )

print("====================================")