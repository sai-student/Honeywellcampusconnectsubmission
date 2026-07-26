import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )


from ai_engine.safe_ai_controller import (
    get_safe_ai_action
)


STATE_FILE = (
    PROJECT_ROOT
    / "data"
    / "live_building_state.json"
)


print("\n============================================")
print("       SAFE AUTONOMOUS AI-BMS TEST")
print("============================================")


with open(
    STATE_FILE,
    "r",
    encoding="utf-8"
) as file:

    building_state = json.load(
        file
    )


print("\nCurrent Building State")
print("--------------------------------------------")

print(
    "Simulation time:",
    building_state.get(
        "simulation_time"
    )
)

print(
    "Occupancy:",
    building_state.get(
        "total_occupancy"
    )
)

print(
    "Outdoor:",
    building_state.get(
        "outdoor_temperature"
    ),
    "C"
)

print(
    "Current setpoints:",
    building_state.get(
        "current_setpoints"
    )
)


print("\nAsking AI for HVAC action...")
print("--------------------------------------------")


safe_action = get_safe_ai_action(
    building_state
)


print("\nFINAL SAFE ACTION")
print("--------------------------------------------")

print(
    json.dumps(
        safe_action,
        indent=2
    )
)


print("\n============================================")