def validate_ai_decision(state, decision):
    """
    Semantic validation layer for AI-generated HVAC decisions.

    Priorities:
    1. Safety
    2. Occupant thermal comfort
    3. Energy efficiency
    4. Carbon reduction

    The validator prevents unnecessary conditioning while
    retaining strong recovery whenever occupied temperatures
    leave the required 20-26 C comfort range.
    """

    # ========================================================
    # EXTRACT AI DECISION
    # ========================================================

    try:
        heating = float(decision["heating"])
        cooling = float(decision["cooling"])

    except (KeyError, TypeError, ValueError):
        heating = 20.0
        cooling = 26.0

    # ========================================================
    # EXTRACT BUILDING STATE
    # ========================================================

    occupancy = float(
        state.get("total_occupancy", 0) or 0
    )

    min_temp = state.get(
        "min_occupied_temperature"
    )

    max_temp = state.get(
        "max_occupied_temperature"
    )

    carbon_intensity = float(
        state.get(
            "carbon_intensity",
            0.42
        ) or 0.42
    )

    carbon_level = str(
        state.get(
            "carbon_level",
            "moderate"
        )
    ).lower()

    corrections = []

    # ========================================================
    # UNOCCUPIED MODE
    # ========================================================

    if occupancy <= 0:

        # Maximum energy-saving deadband.
        target_heating = 18.0
        target_cooling = 29.0

        if (
            abs(heating - target_heating) > 0.01
            or
            abs(cooling - target_cooling) > 0.01
        ):
            corrections.append(
                "Unoccupied building forced to "
                "energy-saving deadband."
            )

        heating = target_heating
        cooling = target_cooling

    # ========================================================
    # OCCUPIED MODE
    # ========================================================

    else:

        # ----------------------------------------------------
        # CONVERT TEMPERATURE VALUES
        # ----------------------------------------------------

        if min_temp is not None:
            try:
                min_temp = float(min_temp)
            except (TypeError, ValueError):
                min_temp = None

        if max_temp is not None:
            try:
                max_temp = float(max_temp)
            except (TypeError, ValueError):
                max_temp = None

        # ====================================================
        # BASE OCCUPIED LIMITS
        # ====================================================

        if heating < 20.0:
            heating = 20.0

            corrections.append(
                "Occupied heating setpoint raised "
                "to 20 C minimum."
            )

        if cooling > 26.0:
            cooling = 26.0

            corrections.append(
                "Occupied cooling setpoint reduced "
                "to 26 C maximum."
            )

        # ====================================================
        # COLD RECOVERY
        # ====================================================

        if min_temp is not None:

            # Emergency recovery
            if min_temp < 18.5:

                if heating < 22.0:
                    heating = 22.0

                    corrections.append(
                        "Emergency heating recovery applied "
                        "because occupied temperature "
                        "fell below 18.5 C."
                    )

            # Strong recovery
            elif min_temp < 19.0:

                if heating < 21.5:
                    heating = 21.5

                    corrections.append(
                        "Strong heating recovery applied "
                        "because occupied temperature "
                        "fell below 19 C."
                    )

            # Normal comfort recovery
            elif min_temp < 20.0:

                if heating < 21.0:
                    heating = 21.0

                    corrections.append(
                        "Heating recovery applied because "
                        "occupied temperature fell below "
                        "20 C."
                    )

            # -----------------------------------------------
            # ENERGY-EFFICIENT NEAR-BOUNDARY OPERATION
            # -----------------------------------------------
            #
            # 20.0 <= temperature < 20.5 is STILL within
            # the required comfort range.
            #
            # Do not unnecessarily raise heating to 20.5 C.
            #
            elif min_temp < 20.5:

                if heating < 20.0:
                    heating = 20.0

                    corrections.append(
                        "Heating maintained at occupied "
                        "comfort minimum without "
                        "unnecessary preheating."
                    )

        # ====================================================
        # HOT RECOVERY
        # ====================================================

        if max_temp is not None:

            # Emergency cooling
            if max_temp > 27.5:

                if cooling > 23.5:
                    cooling = 23.5

                    corrections.append(
                        "Emergency cooling recovery applied "
                        "because occupied temperature "
                        "exceeded 27.5 C."
                    )

            # Strong cooling
            elif max_temp > 27.0:

                if cooling > 24.0:
                    cooling = 24.0

                    corrections.append(
                        "Strong cooling recovery applied "
                        "because occupied temperature "
                        "exceeded 27 C."
                    )

            # Normal comfort recovery
            elif max_temp > 26.0:

                if cooling > 25.0:
                    cooling = 25.0

                    corrections.append(
                        "Cooling recovery applied because "
                        "occupied temperature exceeded "
                        "26 C."
                    )

            # Preventive cooling retained.
            #
            # Electricity was not the dominant energy problem,
            # so this protection remains conservative.
            elif max_temp > 25.5:

                if cooling > 25.5:
                    cooling = 25.5

                    corrections.append(
                        "Preventive cooling applied near "
                        "the upper comfort boundary."
                    )

        # ====================================================
        # CARBON-AWARE OPTIMIZATION
        # ====================================================
        #
        # Carbon optimization is permitted only when all
        # occupied zones have sufficient comfort reserve.
        # ====================================================

        carbon_safe = (
            min_temp is not None
            and
            max_temp is not None
            and
            min_temp >= 20.5
            and
            max_temp <= 25.5
        )

        if carbon_safe:

            # ------------------------------------------------
            # HIGH CARBON
            # ------------------------------------------------

            if (
                carbon_level == "high"
                or
                carbon_intensity >= 0.50
            ):

                heating = 20.0
                cooling = 26.0

                corrections.append(
                    "High-carbon period detected; "
                    "HVAC deadband widened while "
                    "maintaining occupied comfort."
                )

            # ------------------------------------------------
            # MODERATE CARBON
            # ------------------------------------------------

            elif (
                carbon_level == "moderate"
                or
                carbon_intensity >= 0.35
            ):

                # Do not increase heating unnecessarily.
                heating = max(
                    heating,
                    20.0
                )

                cooling = min(
                    cooling,
                    25.5
                )

            # ------------------------------------------------
            # LOW CARBON
            # ------------------------------------------------

            else:

                # Low-carbon electricity does NOT justify
                # additional natural-gas heating.
                #
                # Maintain energy-efficient occupied limits.
                heating = max(
                    heating,
                    20.0
                )

                cooling = min(
                    cooling,
                    26.0
                )

    # ========================================================
    # FINAL OCCUPIED COMFORT PROTECTION
    # ========================================================

    if occupancy > 0:

        heating = max(
            heating,
            20.0
        )

        cooling = min(
            cooling,
            26.0
        )

    # ========================================================
    # PHYSICAL SETPOINT LIMITS
    # ========================================================

    heating = max(
        16.0,
        min(
            22.0,
            heating
        )
    )

    cooling = max(
        23.0,
        min(
            30.0,
            cooling
        )
    )

    # ========================================================
    # MINIMUM THERMOSTAT DEADBAND
    # ========================================================

    minimum_deadband = 2.0

    if cooling - heating < minimum_deadband:

        proposed_cooling = (
            heating
            + minimum_deadband
        )

        if proposed_cooling <= 30.0:

            cooling = proposed_cooling

        else:

            heating = (
                cooling
                - minimum_deadband
            )

        corrections.append(
            "Minimum 2 C thermostat deadband enforced."
        )

    # ========================================================
    # FINAL PHYSICAL VALIDATION
    # ========================================================

    heating = max(
        16.0,
        min(
            22.0,
            heating
        )
    )

    cooling = max(
        23.0,
        min(
            30.0,
            cooling
        )
    )

    # ========================================================
    # RETURN VALIDATED DECISION
    # ========================================================

    return {

        **decision,

        "heating":
            round(
                heating,
                2
            ),

        "cooling":
            round(
                cooling,
                2
            ),

        "semantic_modified":
            len(corrections) > 0,

        "semantic_corrections":
            corrections
    }