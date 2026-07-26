class SafetyGuard:

    # ========================================================
    # ABSOLUTE EQUIPMENT / CONTROL LIMITS
    # ========================================================

    MIN_HEATING = 18.0
    MAX_HEATING = 22.0

    # Semantic validator may request 23.5 C during
    # emergency cooling recovery.
    MIN_COOLING = 23.0
    MAX_COOLING = 29.0

    MIN_DEADBAND = 2.0

    # Normal maximum change per AI decision.
    MAX_SETPOINT_CHANGE = 2.0

    # Larger change allowed when semantic validation
    # requests urgent comfort recovery.
    EMERGENCY_SETPOINT_CHANGE = 3.0


    @staticmethod
    def validate(
        proposed_heating,
        proposed_cooling,
        current_heating,
        current_cooling
    ):

        # ====================================================
        # CONVERT INPUTS
        # ====================================================

        heating = float(
            proposed_heating
        )

        cooling = float(
            proposed_cooling
        )

        current_heating = float(
            current_heating
        )

        current_cooling = float(
            current_cooling
        )

        modified = False
        reasons = []


        # ====================================================
        # ABSOLUTE HEATING LIMITS
        # ====================================================

        if heating < SafetyGuard.MIN_HEATING:

            heating = SafetyGuard.MIN_HEATING
            modified = True

            reasons.append(
                "Heating limited to minimum 18 C."
            )


        elif heating > SafetyGuard.MAX_HEATING:

            heating = SafetyGuard.MAX_HEATING
            modified = True

            reasons.append(
                "Heating limited to maximum 22 C."
            )


        # ====================================================
        # ABSOLUTE COOLING LIMITS
        # ====================================================

        if cooling < SafetyGuard.MIN_COOLING:

            cooling = SafetyGuard.MIN_COOLING
            modified = True

            reasons.append(
                "Cooling limited to minimum 23 C."
            )


        elif cooling > SafetyGuard.MAX_COOLING:

            cooling = SafetyGuard.MAX_COOLING
            modified = True

            reasons.append(
                "Cooling limited to maximum 29 C."
            )


        # ====================================================
        # DETERMINE WHETHER STRONGER RECOVERY IS REQUIRED
        # ====================================================

        heating_change = (
            heating
            - current_heating
        )

        cooling_change = (
            cooling
            - current_cooling
        )


        # If semantic validation is asking for a large
        # movement toward stronger conditioning, allow a
        # slightly larger safety-controlled step.

        heating_recovery = (
            heating >= 21.0
            and heating > current_heating
        )

        cooling_recovery = (
            cooling <= 24.5
            and cooling < current_cooling
        )


        # ====================================================
        # HEATING RATE LIMIT
        # ====================================================

        if heating_recovery:

            heating_limit = (
                SafetyGuard.EMERGENCY_SETPOINT_CHANGE
            )

        else:

            heating_limit = (
                SafetyGuard.MAX_SETPOINT_CHANGE
            )


        if abs(heating_change) > heating_limit:

            if heating_change > 0:

                heating = (
                    current_heating
                    + heating_limit
                )

            else:

                heating = (
                    current_heating
                    - heating_limit
                )

            modified = True

            reasons.append(
                "Heating change rate limited for "
                "safe HVAC operation."
            )


        # ====================================================
        # COOLING RATE LIMIT
        # ====================================================

        if cooling_recovery:

            cooling_limit = (
                SafetyGuard.EMERGENCY_SETPOINT_CHANGE
            )

        else:

            cooling_limit = (
                SafetyGuard.MAX_SETPOINT_CHANGE
            )


        if abs(cooling_change) > cooling_limit:

            if cooling_change > 0:

                cooling = (
                    current_cooling
                    + cooling_limit
                )

            else:

                cooling = (
                    current_cooling
                    - cooling_limit
                )

            modified = True

            reasons.append(
                "Cooling change rate limited for "
                "safe HVAC operation."
            )


        # ====================================================
        # SECOND ABSOLUTE CLAMP
        # ====================================================

        heating = max(
            SafetyGuard.MIN_HEATING,
            min(
                SafetyGuard.MAX_HEATING,
                heating
            )
        )

        cooling = max(
            SafetyGuard.MIN_COOLING,
            min(
                SafetyGuard.MAX_COOLING,
                cooling
            )
        )


        # ====================================================
        # DEAD BAND PROTECTION
        # ====================================================

        if (
            cooling - heating
            < SafetyGuard.MIN_DEADBAND
        ):

            # First try increasing cooling.
            required_cooling = (
                heating
                + SafetyGuard.MIN_DEADBAND
            )

            if (
                required_cooling
                <= SafetyGuard.MAX_COOLING
            ):

                cooling = required_cooling

            else:

                # If cooling cannot be increased safely,
                # reduce heating instead.
                heating = (
                    cooling
                    - SafetyGuard.MIN_DEADBAND
                )

            modified = True

            reasons.append(
                "Setpoints adjusted to maintain "
                "minimum 2 C HVAC deadband."
            )


        # ====================================================
        # FINAL DEFENSIVE CLAMP
        # ====================================================

        heating = max(
            SafetyGuard.MIN_HEATING,
            min(
                SafetyGuard.MAX_HEATING,
                heating
            )
        )

        cooling = max(
            SafetyGuard.MIN_COOLING,
            min(
                SafetyGuard.MAX_COOLING,
                cooling
            )
        )


        # ====================================================
        # FINAL DEADBAND GUARANTEE
        # ====================================================

        if (
            cooling - heating
            < SafetyGuard.MIN_DEADBAND
        ):

            heating = min(
                heating,
                cooling
                - SafetyGuard.MIN_DEADBAND
            )

            heating = max(
                SafetyGuard.MIN_HEATING,
                heating
            )

            modified = True

            reasons.append(
                "Final safety correction applied "
                "to thermostat deadband."
            )


        # ====================================================
        # RETURN APPROVED ACTION
        # ====================================================

        return {

            "heating_setpoint":
                round(
                    heating,
                    2
                ),

            "cooling_setpoint":
                round(
                    cooling,
                    2
                ),

            "modified":
                modified,

            "reasons":
                reasons
        }