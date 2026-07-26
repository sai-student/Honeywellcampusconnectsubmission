import json
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOG_DIR = PROJECT_ROOT / "logs"

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)

LOG_FILE = LOG_DIR / "ai_decisions.jsonl"


def log_ai_decision(
    building_state,
    raw_decision,
    validated_decision,
    safe_action
):

    record = {

        "timestamp": datetime.now().isoformat(),

        "simulation_time": building_state.get(
            "simulation_time"
        ),

        "building_state": {
            "outdoor_temperature":
                building_state.get(
                    "outdoor_temperature"
                ),

            "total_occupancy":
                building_state.get(
                    "total_occupancy"
                ),

            "avg_occupied_temperature":
                building_state.get(
                    "avg_occupied_temperature"
                ),

            "min_occupied_temperature":
                building_state.get(
                    "min_occupied_temperature"
                ),

            "max_occupied_temperature":
                building_state.get(
                    "max_occupied_temperature"
                ),

            "hvac_power_kw":
                building_state.get(
                    "hvac_power_kw"
                ),

            "carbon_intensity":
                building_state.get(
                    "carbon_intensity"
                )
        },

        "current_setpoints":
            building_state.get(
                "current_setpoints"
            ),

        "llm_decision":
            raw_decision,

        "validation":
            validated_decision,

        "safe_action":
            safe_action
    }

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            json.dumps(record)
            + "\n"
        )