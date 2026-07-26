from dataclasses import dataclass


@dataclass
class HVACAction:

    heating_setpoint: float

    cooling_setpoint: float

    reason: str

    confidence: float


    def to_dict(self):

        return {
            "heating_setpoint":
                self.heating_setpoint,

            "cooling_setpoint":
                self.cooling_setpoint,

            "reason":
                self.reason,

            "confidence":
                self.confidence
        }