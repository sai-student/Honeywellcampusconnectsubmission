import json
import os

from mcp.server.fastmcp import FastMCP
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

LIVE_STATE_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "live_building_state.json"
)
mcp = FastMCP(
    "Autonomous AI-BMS"
)


@mcp.tool()
def get_system_status() -> dict:
    """
    Return the current status of the AI-BMS.
    """

    return {
        "system": "Autonomous AI-BMS",
        "energyplus": "configured",
        "controller": "ready",
        "safety_guard": "enabled",
        "mcp": "running"
    }
@mcp.tool()
def get_building_state() -> dict:
    """
    Return the latest building state generated
    by the EnergyPlus simulation.
    """

    if not os.path.exists(LIVE_STATE_FILE):

        return {
            "status": "unavailable",
            "error": "Live EnergyPlus state file does not exist."
        }

    try:

        with open(
            LIVE_STATE_FILE,
            "r"
        ) as file:

            state = json.load(file)

        return state

    except Exception as error:

        return {
            "status": "error",
            "error": str(error)
        }

@mcp.tool()
def validate_hvac_action(
    heating_setpoint: float,
    cooling_setpoint: float
) -> dict:
    """
    Perform basic validation of proposed HVAC setpoints.
    """

    reasons = []

    heating = heating_setpoint
    cooling = cooling_setpoint

    if heating < 18:
        heating = 18
        reasons.append(
            "Heating limited to minimum 18 C."
        )

    if heating > 22:
        heating = 22
        reasons.append(
            "Heating limited to maximum 22 C."
        )

    if cooling < 23:
        cooling = 23
        reasons.append(
            "Cooling limited to minimum 23 C."
        )

    if cooling > 29:
        cooling = 29
        reasons.append(
            "Cooling limited to maximum 29 C."
        )

    if cooling - heating < 2:
        cooling = heating + 2

        reasons.append(
            "Cooling adjusted to maintain 2 C deadband."
        )

    return {
        "heating_setpoint": heating,
        "cooling_setpoint": cooling,
        "modified": len(reasons) > 0,
        "reasons": reasons
    }


if __name__ == "__main__":
    mcp.run()