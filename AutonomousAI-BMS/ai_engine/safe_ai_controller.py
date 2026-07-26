from ai_engine.decision_engine import get_ai_decision
from ai_engine.action_validator import validate_llm_response
from ai_engine.decision_logger import log_ai_decision
from ai_engine.decision_validator import validate_ai_decision
from controller.safety_guard import SafetyGuard


def get_safe_ai_action(building_state):

    # ========================================================
    # CURRENT SETPOINTS
    # ========================================================

    current_heating = float(
        building_state["current_setpoints"]["heating"]
    )

    current_cooling = float(
        building_state["current_setpoints"]["cooling"]
    )


    # ========================================================
    # ASK LLM
    # ========================================================

    raw_decision = get_ai_decision(
        building_state
    )


    # ========================================================
    # LLM FAILURE FALLBACK
    # ========================================================

    if raw_decision is None:

        safe_action = {
            "heating_setpoint": current_heating,
            "cooling_setpoint": current_cooling,

            "modified": True,

            "reasons": [
                "LLM unavailable. Current HVAC setpoints retained."
            ],

            "ai_reason": "LLM unavailable.",

            "energy_strategy":
                "Fallback to existing HVAC settings.",

            "comfort_risk": "unknown",

            "semantic_modified": False,

            "semantic_corrections": [],

            # Keep dashboard schema consistent
            "raw_llm_decision": {}
        }


        log_ai_decision(
            building_state,
            None,
            {
                "valid": False,
                "reason": "LLM unavailable"
            },
            safe_action
        )

        return safe_action


    # ========================================================
    # STRUCTURAL VALIDATION
    # ========================================================

    validation = validate_llm_response(
        raw_decision
    )


    # ========================================================
    # INVALID LLM RESPONSE FALLBACK
    # ========================================================

    if not validation["valid"]:

        safe_action = {
            "heating_setpoint": current_heating,
            "cooling_setpoint": current_cooling,

            "modified": True,

            "reasons": [
                "Invalid LLM response. Current HVAC setpoints retained."
            ],

            "ai_reason": raw_decision.get(
                "reason",
                ""
            ),

            "energy_strategy": raw_decision.get(
                "energy_strategy",
                ""
            ),

            "comfort_risk": raw_decision.get(
                "comfort_risk",
                "unknown"
            ),

            "semantic_modified": False,

            "semantic_corrections": [],

            # Preserve invalid proposal for audit/dashboard
            "raw_llm_decision": raw_decision
        }


        log_ai_decision(
            building_state,
            raw_decision,
            validation,
            safe_action
        )

        return safe_action


    # ========================================================
    # SEMANTIC VALIDATION
    # ========================================================

    validated_decision = validate_ai_decision(
        building_state,
        raw_decision
    )


    # ========================================================
    # DETERMINISTIC SAFETY GUARD
    # ========================================================

    safe_action = SafetyGuard.validate(

        proposed_heating=float(
            validated_decision["heating"]
        ),

        proposed_cooling=float(
            validated_decision["cooling"]
        ),

        current_heating=current_heating,

        current_cooling=current_cooling
    )


    # ========================================================
    # BUILDING CONTEXT FOR EXPLANATION
    # ========================================================

    occupancy = float(
        building_state.get(
            "total_occupancy",
            0
        ) or 0
    )

    min_temp = building_state.get(
        "min_occupied_temperature"
    )

    max_temp = building_state.get(
        "max_occupied_temperature"
    )


    # ========================================================
    # ORIGINAL LLM EXPLANATION
    # ========================================================

    ai_reason = raw_decision.get(
        "reason",
        ""
    )

    energy_strategy = raw_decision.get(
        "energy_strategy",
        ""
    )

    comfort_risk = raw_decision.get(
        "comfort_risk",
        "unknown"
    )


    # ========================================================
    # EXPLANATION CONSISTENCY GUARD
    # ========================================================

    if occupancy <= 0:

        ai_reason = (
            "Building is unoccupied; HVAC is operating "
            "in energy-saving mode."
        )

        energy_strategy = (
            "Use a wider heating/cooling deadband to "
            "reduce unnecessary HVAC energy consumption."
        )

        comfort_risk = "low"


    else:

        # ----------------------------------------------------
        # OCCUPIED + VERY HOT
        # ----------------------------------------------------

        if (
            max_temp is not None
            and float(max_temp) >= 27.0
        ):

            ai_reason = (
                "Occupied zones are above the comfort "
                "temperature range, so stronger cooling "
                "is required."
            )

            energy_strategy = (
                "Prioritize occupant comfort while using "
                "the minimum cooling adjustment required."
            )

            comfort_risk = "high"


        # ----------------------------------------------------
        # OCCUPIED + SLIGHTLY HOT
        # ----------------------------------------------------

        elif (
            max_temp is not None
            and float(max_temp) > 26.0
        ):

            ai_reason = (
                "Occupied zones are slightly above the "
                "comfort temperature range."
            )

            energy_strategy = (
                "Maintain sufficient cooling while avoiding "
                "unnecessary HVAC energy consumption."
            )

            comfort_risk = "medium"


        # ----------------------------------------------------
        # OCCUPIED + VERY COLD
        # ----------------------------------------------------

        elif (
            min_temp is not None
            and float(min_temp) <= 19.0
        ):

            ai_reason = (
                "Occupied zones are below the comfort "
                "temperature range, so additional heating "
                "is required."
            )

            energy_strategy = (
                "Prioritize occupant comfort while limiting "
                "heating to the required level."
            )

            comfort_risk = "high"


        # ----------------------------------------------------
        # OCCUPIED + SLIGHTLY COLD
        # ----------------------------------------------------

        elif (
            min_temp is not None
            and float(min_temp) < 20.0
        ):

            ai_reason = (
                "Occupied zones are slightly below the "
                "comfort temperature range."
            )

            energy_strategy = (
                "Maintain sufficient heating while minimizing "
                "unnecessary HVAC operation."
            )

            comfort_risk = "medium"


        # ----------------------------------------------------
        # OCCUPIED + COMFORTABLE
        # ----------------------------------------------------

        else:

            ai_reason = (
                "Occupied zones are within the acceptable "
                "comfort temperature range."
            )

            energy_strategy = (
                "Optimize HVAC energy consumption while "
                "maintaining occupant comfort."
            )

            comfort_risk = "low"


    # ========================================================
    # ATTACH EXPLANATION
    # ========================================================

    safe_action["ai_reason"] = ai_reason

    safe_action["energy_strategy"] = (
        energy_strategy
    )

    safe_action["comfort_risk"] = (
        comfort_risk
    )


    # ========================================================
    # SEMANTIC GUARD RESULTS
    # ========================================================

    safe_action["semantic_modified"] = (
        validated_decision[
            "semantic_modified"
        ]
    )

    safe_action["semantic_corrections"] = (
        validated_decision[
            "semantic_corrections"
        ]
    )


    # ========================================================
    # PRESERVE ORIGINAL LLM PROPOSAL
    # ========================================================

    safe_action["raw_llm_decision"] = {

        "heating": raw_decision.get(
            "heating"
        ),

        "cooling": raw_decision.get(
            "cooling"
        ),

        "reason": raw_decision.get(
            "reason",
            ""
        ),

        "energy_strategy": raw_decision.get(
            "energy_strategy",
            ""
        ),

        "comfort_risk": raw_decision.get(
            "comfort_risk",
            "unknown"
        )
    }


    # ========================================================
    # LOG COMPLETE DECISION PIPELINE
    # ========================================================

    log_ai_decision(
        building_state,
        raw_decision,
        validation,
        safe_action
    )


    # ========================================================
    # RETURN FINAL APPROVED ACTION
    # ========================================================

    return safe_action