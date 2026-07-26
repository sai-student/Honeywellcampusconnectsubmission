def validate_llm_response(decision):
    """
    Validate the structure and types of an LLM HVAC decision.
    This does NOT enforce physical safety limits.
    SafetyGuard handles those separately.
    """

    if not isinstance(decision, dict):
        return {
            "valid": False,
            "reason": "LLM response is not a JSON object."
        }

    required_fields = [
        "heating",
        "cooling",
        "reason",
        "energy_strategy",
        "comfort_risk"
    ]

    for field in required_fields:
        if field not in decision:
            return {
                "valid": False,
                "reason": f"Missing required field: {field}"
            }

    try:
        heating = float(decision["heating"])
        cooling = float(decision["cooling"])
    except (TypeError, ValueError):
        return {
            "valid": False,
            "reason": "Heating/cooling values are not numeric."
        }

    if decision["comfort_risk"] not in [
        "low",
        "medium",
        "high"
    ]:
        return {
            "valid": False,
            "reason": "Invalid comfort_risk value."
        }

    return {
        "valid": True,
        "heating": heating,
        "cooling": cooling
    }