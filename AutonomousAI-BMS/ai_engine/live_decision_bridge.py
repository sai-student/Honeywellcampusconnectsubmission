import json
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DECISION_FILE = (
    PROJECT_ROOT
    / "data"
    / "live_ai_decision.json"
)


def write_live_ai_decision(
    simulation_time,
    building_state,
    raw_decision,
    safe_action,
    ai_call_number
):
    """
    Write the latest AI-BMS decision for the dashboard.

    Pipeline:
    LLM Proposal
        ->
    Semantic Guard
        ->
    Safety Guard
        ->
    Final HVAC Action
    """

    current_setpoints = building_state.get(
        "current_setpoints",
        {}
    )

    raw_decision = raw_decision or {}
    safe_action = safe_action or {}

    data = {

        "status": "active",

        "updated_at": datetime.now().isoformat(),

        "simulation_time": simulation_time,

        "ai_call_number": ai_call_number,


        # ====================================================
        # BUILDING CONTEXT
        # ====================================================

        "building_context": {

            "occupancy": building_state.get(
                "total_occupancy"
            ),

            "avg_temperature": building_state.get(
                "avg_occupied_temperature"
            ),

            "min_temperature": building_state.get(
                "min_occupied_temperature"
            ),

            "max_temperature": building_state.get(
                "max_occupied_temperature"
            ),

            "outdoor_temperature": building_state.get(
                "outdoor_temperature"
            ),

            "hvac_power_kw": building_state.get(
                "hvac_power_kw"
            ),

            "carbon_intensity": building_state.get(
                "carbon_intensity"
            ),
            "carbon_level": building_state.get(
                "carbon_level",
                "unknown"
            )

        },


        # ====================================================
        # PREVIOUS HVAC STATE
        # ====================================================

        "previous_setpoints": {

            "heating": current_setpoints.get(
                "heating"
            ),

            "cooling": current_setpoints.get(
                "cooling"
            )
        },


        # ====================================================
        # ORIGINAL LLM PROPOSAL
        # ====================================================

        "llm_proposal": {

            "heating": raw_decision.get(
                "heating"
            ),

            "cooling": raw_decision.get(
                "cooling"
            )
        },


        # ====================================================
        # FINAL APPROVED ACTION
        # ====================================================

        "approved_action": {

            "heating": safe_action.get(
                "heating_setpoint"
            ),

            "cooling": safe_action.get(
                "cooling_setpoint"
            )
        },


        # ====================================================
        # AI EXPLANATION
        # ====================================================

        "reason": safe_action.get(
            "ai_reason",
            raw_decision.get(
                "reason",
                ""
            )
        ),

        "energy_strategy": safe_action.get(
            "energy_strategy",
            raw_decision.get(
                "energy_strategy",
                ""
            )
        ),

        "comfort_risk": safe_action.get(
            "comfort_risk",
            raw_decision.get(
                "comfort_risk",
                "unknown"
            )
        ),


        # ====================================================
        # SEMANTIC GUARD
        # ====================================================

        "semantic_modified": safe_action.get(
            "semantic_modified",
            False
        ),

        "semantic_corrections": safe_action.get(
            "semantic_corrections",
            []
        ),


        # ====================================================
        # SAFETY GUARD
        # ====================================================

        "safety_modified": safe_action.get(
            "modified",
            False
        ),

        "safety_corrections": safe_action.get(
            "reasons",
            []
        )
    }


    # Ensure data directory exists
    DECISION_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    # Write directly.
    # This avoids the Windows os.replace locking problem.
    with open(
        DECISION_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2
        )

        file.flush()


    return data