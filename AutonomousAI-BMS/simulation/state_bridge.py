import json
import os
import time
from datetime import datetime


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

STATE_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "live_building_state.json"
)


def write_building_state(
    simulation_time,
    outdoor_temperature,
    zone_temperatures,
    occupancies,
    heating_setpoint,
    cooling_setpoint,
    hvac_power_kw=None,
    carbon_intensity=None
):
    """
    Write latest EnergyPlus building state.

    Uses direct file writing with retries to avoid
    Windows os.replace locking problems.
    """

    total_occupancy = sum(occupancies)

    occupied_temperatures = [
        temp
        for temp, occ in zip(
            zone_temperatures,
            occupancies
        )
        if occ > 0
    ]

    if occupied_temperatures:

        avg_occupied_temperature = (
            sum(occupied_temperatures)
            / len(occupied_temperatures)
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


    zones = []

    for index, (temperature, occupancy) in enumerate(
        zip(zone_temperatures, occupancies),
        start=1
    ):

        zones.append({
            "name": f"SPACE{index}-1",

            "temperature": round(
                float(temperature),
                2
            ),

            "occupancy": round(
                float(occupancy),
                2
            )
        })


    state = {

        "status": "running",

        "updated_at": datetime.now().isoformat(),

        "simulation_time": simulation_time,

        "outdoor_temperature": round(
            float(outdoor_temperature),
            2
        ),

        "zones": zones,

        "total_occupancy": round(
            float(total_occupancy),
            2
        ),

        "avg_occupied_temperature": (
            round(
                float(avg_occupied_temperature),
                2
            )
            if avg_occupied_temperature is not None
            else None
        ),

        "min_occupied_temperature": (
            round(
                float(min_occupied_temperature),
                2
            )
            if min_occupied_temperature is not None
            else None
        ),

        "max_occupied_temperature": (
            round(
                float(max_occupied_temperature),
                2
            )
            if max_occupied_temperature is not None
            else None
        ),

        "current_setpoints": {

            "heating": round(
                float(heating_setpoint),
                2
            ),

            "cooling": round(
                float(cooling_setpoint),
                2
            )
        },

        "hvac_power_kw": hvac_power_kw,

        "carbon_intensity": carbon_intensity
    }


    # Make sure data directory exists
    os.makedirs(
        os.path.dirname(STATE_FILE),
        exist_ok=True
    )


    # --------------------------------------------------------
    # WINDOWS-SAFE WRITE
    # --------------------------------------------------------

    # Retry briefly if MCP happens to be reading the file.
    # --------------------------------------------------------
# ATOMIC WRITE WITH WINDOWS RETRY
# --------------------------------------------------------

    os.makedirs(
        os.path.dirname(STATE_FILE),
        exist_ok=True
    )

    temp_path = STATE_FILE + ".tmp"

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            state,
            file,
            indent=2
        )

        file.flush()

        os.fsync(file.fileno())


    max_attempts = 20

    for attempt in range(max_attempts):

        try:

            os.replace(
                temp_path,
                STATE_FILE
            )

            return True

        except PermissionError:

            if attempt == max_attempts - 1:
                raise

            time.sleep(0.02)


    return False