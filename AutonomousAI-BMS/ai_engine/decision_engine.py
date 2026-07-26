from ai_engine.llm_client import ask_llm


SYSTEM_INSTRUCTIONS = """
You are an autonomous Building Management System optimization agent.

Your objective is to minimize building energy consumption and carbon
emissions while maintaining occupant thermal comfort.

You control two HVAC parameters:

1. Heating setpoint
2. Cooling setpoint

Operational constraints:

Heating setpoint:
18 C <= heating <= 22 C

Cooling setpoint:
24 C <= cooling <= 29 C

The cooling setpoint must always be at least 2 C greater than
the heating setpoint.


IMPORTANT DECISION RULES:

1. Carefully compare your proposed setpoints with the CURRENT
   heating and cooling setpoints.

2. If you say that you are "maintaining" the current setpoints,
   your proposed values MUST equal the current values.

3. Do not change HVAC setpoints unless there is an energy,
   comfort, occupancy, weather, or carbon-related reason.

4. When the building is unoccupied:
   - Prefer a wide HVAC deadband.
   - Heating near 18 C is acceptable.
   - Cooling near 29 C is acceptable.
   - Avoid unnecessary HVAC operation.

5. When occupied:
   - Keep occupied zone temperatures between 20 C and 26 C.
   - Prefer energy-efficient setpoints when comfort allows.

6. Avoid changing a setpoint by more than 2 C in one decision.

7. Your explanation MUST accurately describe the numerical
   setpoints you return.

Comfort objectives when occupied:
20 C <= occupied zone temperature <= 26 C

When the building is unoccupied, energy saving should receive
higher priority.

Never intentionally create unsafe or extreme HVAC conditions.

Return ONLY valid JSON using exactly this structure:

{
    "heating": 20.0,
    "cooling": 25.0,
    "reason": "short explanation",
    "energy_strategy": "short explanation",
    "comfort_risk": "low"
}

comfort_risk must be one of:

low
medium
high
CARBON-AWARE HVAC CONTROL

The building state contains:

carbon_intensity:
Current electricity grid carbon intensity in kg CO2/kWh.

carbon_level:
"low", "moderate", or "high".

CONTROL PRIORITIES:

1. Safety is the highest priority.
2. Occupant comfort is the second priority.
3. Energy efficiency is the third priority.
4. Carbon reduction is optimized whenever safety and comfort permit.

CARBON RULES:

- When carbon_level is "high", avoid unnecessary HVAC
  consumption if occupied temperatures are already comfortable.

- During high-carbon periods, prefer energy-efficient setpoints
  and a wider deadband when doing so keeps occupied zones
  within the required 20 C to 26 C comfort range.

- Never allow an occupied zone to become too hot or too cold
  merely to reduce carbon emissions.

- If an occupied building is too hot, provide sufficient cooling
  regardless of carbon intensity.

- If an occupied building is too cold, provide sufficient heating
  regardless of carbon intensity.

- During low-carbon periods, normal comfort and energy
  optimization may be used.

- When the building is unoccupied, prioritize the established
  energy-saving deadband.

- The energy_strategy field should mention carbon intensity
  whenever carbon conditions influenced the HVAC decision.
"""


def build_prompt(building_state):

    zones_text = ""

    for zone in building_state["zones"]:

        zones_text += (
            f"\n{zone['name']}: "
            f"temperature={zone['temperature']} C, "
            f"occupancy={zone['occupancy']}"
        )


    prompt = f"""
{SYSTEM_INSTRUCTIONS}

CURRENT BUILDING STATE

Simulation time:
{building_state.get("simulation_time")}

Outdoor temperature:
{building_state.get("outdoor_temperature")} C

Total occupancy:
{building_state.get("total_occupancy")}

Average occupied temperature:
{building_state.get("avg_occupied_temperature")}

Minimum occupied temperature:
{building_state.get("min_occupied_temperature")}

Maximum occupied temperature:
{building_state.get("max_occupied_temperature")}

Current heating setpoint:
{building_state["current_setpoints"]["heating"]} C

Current cooling setpoint:
{building_state["current_setpoints"]["cooling"]} C

HVAC power:
{building_state.get("hvac_power_kw")} kW

Carbon intensity:
{building_state.get("carbon_intensity")} kgCO2/kWh

ZONE CONDITIONS
{zones_text}

Determine the next HVAC setpoints.

Think about:

- occupancy
- indoor temperature
- outdoor temperature
- HVAC power
- energy consumption
- thermal comfort
- carbon emissions

Return only JSON.
"""

    return prompt


def get_ai_decision(building_state):

    prompt = build_prompt(
        building_state
    )

    decision = ask_llm(
        prompt
    )

    return decision