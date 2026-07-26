def get_carbon_intensity(hour, month=None):
    """
    Return simulated electricity-grid carbon intensity.

    Unit:
        kg CO2 / kWh

    IMPORTANT:
    This is a synthetic time-varying carbon profile used
    for experimental evaluation. It is NOT real-time
    Chicago grid carbon data.
    """

    hour = int(hour)

    # Overnight
    if 0 <= hour < 6:
        return 0.34

    # Morning demand period
    elif 6 <= hour < 10:
        return 0.43

    # Lower-carbon midday period
    elif 10 <= hour < 16:
        return 0.30

    # Evening peak
    elif 16 <= hour < 21:
        return 0.55

    # Late evening
    else:
        return 0.40


def get_carbon_level(carbon_intensity):
    """
    Convert numerical carbon intensity into a category.
    """

    carbon_intensity = float(carbon_intensity)

    if carbon_intensity < 0.35:
        return "low"

    elif carbon_intensity <= 0.45:
        return "moderate"

    else:
        return "high"


def calculate_carbon_emissions(
    energy_kwh,
    carbon_intensity
):
    """
    Carbon emissions in kg CO2.
    """

    return (
        float(energy_kwh)
        * float(carbon_intensity)
    )