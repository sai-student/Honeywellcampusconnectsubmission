import pandas as pd


FILE = "data/baseline_building.csv"

df = pd.read_csv(FILE)


facility = df["facility_energy_kwh"].sum()

hvac = df["hvac_energy_kwh"].sum()

avg_temp = df["avg_indoor_temp_c"].mean()

avg_humidity = df["avg_humidity_pct"].mean()

max_occupancy = df["total_occupancy"].max()

occupied = df[df["total_occupancy"] > 0]


print("\n================================")
print("   AI-BMS BASELINE REPORT")
print("================================")

print(
    f"\nAnnual Facility Electricity : "
    f"{facility:,.2f} kWh"
)

print(
    f"Annual HVAC Electricity     : "
    f"{hvac:,.2f} kWh"
)

if facility > 0:

    hvac_percentage = (
        hvac / facility
    ) * 100

    print(
        f"HVAC Share                 : "
        f"{hvac_percentage:.2f}%"
    )


print(
    f"\nAverage Indoor Temperature : "
    f"{avg_temp:.2f} °C"
)

print(
    f"Average Relative Humidity  : "
    f"{avg_humidity:.2f}%"
)

print(
    f"Maximum Occupancy          : "
    f"{max_occupancy:.0f}"
)


if not occupied.empty:

    print(
        f"\nOccupied Hours             : "
        f"{len(occupied)}"
    )

    print(
        f"Occupied Avg Temperature   : "
        f"{occupied['avg_indoor_temp_c'].mean():.2f} °C"
    )

    print(
        f"Occupied HVAC Electricity  : "
        f"{occupied['hvac_energy_kwh'].sum():,.2f} kWh"
    )


print("\n================================")