import sys
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from ai_engine.safe_ai_controller import (
    get_safe_ai_action
)


SCENARIOS = [

    # ========================================================
    # EMPTY BUILDING
    # ========================================================

    {
        "name": "Empty building",

        "state": {
            "simulation_time": "02:00",

            "outdoor_temperature": 10.0,

            "total_occupancy": 0,

            "avg_occupied_temperature": None,
            "min_occupied_temperature": None,
            "max_occupied_temperature": None,

            "zones": [
                {
                    "name": f"SPACE{i}-1",
                    "temperature": 20.0,
                    "occupancy": 0
                }
                for i in range(1, 6)
            ],

            "current_setpoints": {
                "heating": 18.0,
                "cooling": 29.0
            },

            "hvac_power_kw": 0.2,
            "carbon_intensity": 0.42
        }
    },


    # ========================================================
    # NORMAL OCCUPIED BUILDING
    # ========================================================

    {
        "name": "Comfortable occupied building",

        "state": {
            "simulation_time": "11:00",

            "outdoor_temperature": 28.0,

            "total_occupancy": 52,

            "avg_occupied_temperature": 23.5,
            "min_occupied_temperature": 22.8,
            "max_occupied_temperature": 24.3,

            "zones": [
                {
                    "name": f"SPACE{i}-1",
                    "temperature": 23.5,
                    "occupancy": 10
                }
                for i in range(1, 6)
            ],

            "current_setpoints": {
                "heating": 20.0,
                "cooling": 25.0
            },

            "hvac_power_kw": 4.5,
            "carbon_intensity": 0.42
        }
    },


    # ========================================================
    # HOT OCCUPIED BUILDING
    # ========================================================

    {
        "name": "Hot occupied building",

        "state": {
            "simulation_time": "15:00",

            "outdoor_temperature": 35.0,

            "total_occupancy": 52,

            "avg_occupied_temperature": 26.3,
            "min_occupied_temperature": 25.5,
            "max_occupied_temperature": 27.1,

            "zones": [
                {
                    "name": f"SPACE{i}-1",
                    "temperature": 26.3,
                    "occupancy": 10
                }
                for i in range(1, 6)
            ],

            "current_setpoints": {
                "heating": 19.0,
                "cooling": 26.0
            },

            "hvac_power_kw": 6.8,
            "carbon_intensity": 0.42
        }
    }
]


print("\n============================================")
print("        AI-BMS SCENARIO TEST SUITE")
print("============================================")


for scenario in SCENARIOS:

    print(
        "\n\nSCENARIO:",
        scenario["name"]
    )

    print(
        "--------------------------------------------"
    )

    action = get_safe_ai_action(
        scenario["state"]
    )

    print(
        json.dumps(
            action,
            indent=2
        )
    )


print("\n============================================")
print("Scenario testing complete.")
print("============================================")