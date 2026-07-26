from dataclasses import dataclass, asdict
from typing import List


@dataclass
class ZoneState:

    name: str
    temperature: float
    humidity: float
    occupancy: float


@dataclass
class BuildingState:

    outdoor_temperature: float

    zones: List[ZoneState]

    total_occupancy: float

    avg_occupied_temperature: float | None
    max_occupied_temperature: float | None
    min_occupied_temperature: float | None

    heating_setpoint: float
    cooling_setpoint: float

    hvac_power_kw: float

    carbon_intensity: float | None = None


    def to_dict(self):

        return asdict(self)