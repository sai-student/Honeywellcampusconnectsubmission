from state_bridge import write_building_state


write_building_state(

    simulation_time="01/01 12:00",

    outdoor_temperature=31.5,

    zone_temperatures=[
        23.5,
        24.0,
        23.8,
        24.2,
        22.9
    ],

    occupancies=[
        10,
        8,
        12,
        8,
        0
    ],

    heating_setpoint=20.0,

    cooling_setpoint=25.0,

    hvac_power_kw=4.7,

    carbon_intensity=0.42
)


print(
    "Live building state written successfully."
)