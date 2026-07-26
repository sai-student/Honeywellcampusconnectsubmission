import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

STATE_FILE = (
    PROJECT_ROOT
    / "data"
    / "live_building_state.json"
)

DECISION_FILE = (
    PROJECT_ROOT
    / "data"
    / "live_ai_decision.json"
)


st.set_page_config(
    page_title="Autonomous AI-BMS",
    page_icon="🏢",
    layout="wide"
)


# ============================================================
# AUTO REFRESH
# ============================================================

# Refresh dashboard every 3 seconds.
# Do NOT use while True, time.sleep(), or st.rerun().
st_autorefresh(
    interval=3000,
    key="bms_dashboard_refresh"
)


# ============================================================
# HELPERS
# ============================================================

def read_json_file(path):
    """
    Safely read a JSON file that may be updated by
    another process.
    """

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except FileNotFoundError:
        return None

    except json.JSONDecodeError:
        return None

    except PermissionError:
        return None

    except OSError:
        return None


def format_number(
    value,
    decimals=2,
    suffix=""
):
    """
    Safely format numeric values.
    """

    if value is None:
        return "N/A"

    try:

        return (
            f"{float(value):.{decimals}f}"
            f"{suffix}"
        )

    except (ValueError, TypeError):
        return str(value)


def format_setpoint(value):

    if value is None:
        return "-"

    try:
        return f"{float(value):.1f} °C"

    except (ValueError, TypeError):
        return str(value)


# ============================================================
# READ LIVE FILES
# ============================================================

state = read_json_file(
    STATE_FILE
)

decision = read_json_file(
    DECISION_FILE
)


# ============================================================
# TITLE
# ============================================================

st.title(
    "Autonomous AI Building Management System"
)

st.caption(
    "EnergyPlus + Local Qwen LLM + "
    "Semantic Guard + Deterministic Safety Guard"
)


# ============================================================
# CHECK BUILDING STATE
# ============================================================

if state is None:

    st.error(
        "Live building state is unavailable."
    )

    st.info(
        "Start the EnergyPlus AI controller using: "
        "python simulation\\run_ai_control.py"
    )

    st.stop()


# ============================================================
# SYSTEM STATUS
# ============================================================

st.subheader(
    "System Status"
)


status = str(
    state.get(
        "status",
        "unknown"
    )
).upper()


simulation_time = state.get(
    "simulation_time",
    "-"
)


occupancy = state.get(
    "total_occupancy",
    0
)


outdoor_temperature = state.get(
    "outdoor_temperature"
)


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "System",
        status
    )


with col2:

    st.metric(
        "Simulation Time",
        simulation_time
    )


with col3:

    st.metric(
        "Total Occupancy",
        format_number(
            occupancy,
            1
        )
    )


with col4:

    st.metric(
        "Outdoor Temperature",
        format_number(
            outdoor_temperature,
            2,
            " °C"
        )
    )


# ============================================================
# ENERGY + COMFORT STATE
# ============================================================

st.subheader(
    "Building Energy & Comfort State"
)


hvac_power = state.get(
    "hvac_power_kw"
)


carbon_intensity = state.get(
    "carbon_intensity"
)


avg_temperature = state.get(
    "avg_occupied_temperature"
)


min_temperature = state.get(
    "min_occupied_temperature"
)


max_temperature = state.get(
    "max_occupied_temperature"
)


current_setpoints = state.get(
    "current_setpoints",
    {}
)


current_heating = current_setpoints.get(
    "heating"
)


current_cooling = current_setpoints.get(
    "cooling"
)


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "HVAC Power",
        format_number(
            hvac_power,
            4,
            " kW"
        )
    )


with col2:

    st.metric(
        "Carbon Intensity",
        format_number(
            carbon_intensity,
            3
        )
    )


with col3:

    if avg_temperature is None:

        st.metric(
            "Average Occupied Temp",
            "Unoccupied"
        )

    else:

        st.metric(
            "Average Occupied Temp",
            format_number(
                avg_temperature,
                2,
                " °C"
            )
        )


with col4:

    st.metric(
        "Current HVAC",
        (
            f"{format_number(current_heating, 1)} / "
            f"{format_number(current_cooling, 1)} °C"
        )
    )


# ============================================================
# TEMPERATURE RANGE
# ============================================================

st.markdown(
    "#### Occupied Temperature Range"
)


col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "Minimum",
        (
            format_number(
                min_temperature,
                2,
                " °C"
            )
            if min_temperature is not None
            else "N/A"
        )
    )


with col2:

    st.metric(
        "Average",
        (
            format_number(
                avg_temperature,
                2,
                " °C"
            )
            if avg_temperature is not None
            else "N/A"
        )
    )


with col3:

    st.metric(
        "Maximum",
        (
            format_number(
                max_temperature,
                2,
                " °C"
            )
            if max_temperature is not None
            else "N/A"
        )
    )


# ============================================================
# ZONE CONDITIONS
# ============================================================

st.divider()

st.subheader(
    "Live Zone Conditions"
)


zones = state.get(
    "zones",
    []
)


if zones:

    zone_rows = []

    for zone in zones:

        zone_rows.append({

            "Zone":
                zone.get(
                    "name",
                    "-"
                ),

            "Temperature (°C)":
                zone.get(
                    "temperature"
                ),

            "Occupancy":
                zone.get(
                    "occupancy"
                )
        })


    zone_df = pd.DataFrame(
        zone_rows
    )


    st.dataframe(
        zone_df,
        width="stretch",
        hide_index=True
    )


    # --------------------------------------------------------
    # Zone temperature chart
    # --------------------------------------------------------

    if (
        "Zone" in zone_df.columns
        and
        "Temperature (°C)" in zone_df.columns
    ):

        chart_df = (
            zone_df[
                [
                    "Zone",
                    "Temperature (°C)"
                ]
            ]
            .set_index(
                "Zone"
            )
        )


        st.markdown(
            "#### Zone Temperature Distribution"
        )


        st.bar_chart(
            chart_df,
            width="stretch"
        )


else:

    st.info(
        "No zone data available."
    )


# ============================================================
# AI DECISION AVAILABILITY
# ============================================================

st.divider()

st.header(
    "Autonomous AI Control"
)


if decision is None:

    st.warning(
        "Waiting for the first AI control decision."
    )

    st.info(
        "Keep simulation\\run_ai_control.py running "
        "until AI call 1 is generated."
    )

else:

    # ========================================================
    # AI STATUS
    # ========================================================

    ai_call_number = decision.get(
        "ai_call_number",
        0
    )


    ai_simulation_time = decision.get(
        "simulation_time",
        "-"
    )


    decision_status = str(
        decision.get(
            "status",
            "unknown"
        )
    ).upper()


    updated_at = decision.get(
        "updated_at",
        "-"
    )


    col1, col2, col3, col4 = st.columns(4)


    with col1:

        st.metric(
            "AI Call",
            ai_call_number
        )


    with col2:

        st.metric(
            "AI Simulation Time",
            ai_simulation_time
        )


    with col3:

        st.metric(
            "Decision Status",
            decision_status
        )


    with col4:

        st.metric(
            "Controller",
            "Qwen LLM"
        )


    # ========================================================
    # BUILDING CONTEXT USED BY AI
    # ========================================================

    st.subheader(
        "Building Context Used by AI"
    )


    context = decision.get(
        "building_context",
        {}
    )


    context_occupancy = context.get(
        "occupancy"
    )


    context_avg_temp = context.get(
        "avg_temperature"
    )


    context_outdoor_temp = context.get(
        "outdoor_temperature"
    )


    context_power = context.get(
        "hvac_power_kw"
    )


    col1, col2, col3, col4 = st.columns(4)


    with col1:

        st.metric(
            "Occupancy",
            format_number(
                context_occupancy,
                1
            )
        )


    with col2:

        st.metric(
            "Average Temp",
            (
                format_number(
                    context_avg_temp,
                    2,
                    " °C"
                )
                if context_avg_temp is not None
                else "N/A"
            )
        )


    with col3:

        st.metric(
            "Outdoor Temp",
            format_number(
                context_outdoor_temp,
                2,
                " °C"
            )
        )


    with col4:

        st.metric(
            "HVAC Power",
            format_number(
                context_power,
                4,
                " kW"
            )
        )


    # ========================================================
    # DECISION PIPELINE
    # ========================================================

    st.subheader(
        "AI Decision Pipeline"
    )


    previous = decision.get(
        "previous_setpoints",
        {}
    )


    proposal = decision.get(
        "llm_proposal",
        {}
    )


    approved = decision.get(
        "approved_action",
        {}
    )


    previous_heating = previous.get(
        "heating"
    )

    previous_cooling = previous.get(
        "cooling"
    )


    proposed_heating = proposal.get(
        "heating"
    )

    proposed_cooling = proposal.get(
        "cooling"
    )


    approved_heating = approved.get(
        "heating"
    )

    approved_cooling = approved.get(
        "cooling"
    )


    col1, col2, col3 = st.columns(3)


    # --------------------------------------------------------
    # Previous setpoints
    # --------------------------------------------------------

    with col1:

        st.markdown(
            "### Previous HVAC"
        )

        st.metric(
            "Heating Setpoint",
            format_setpoint(
                previous_heating
            )
        )

        st.metric(
            "Cooling Setpoint",
            format_setpoint(
                previous_cooling
            )
        )


    # --------------------------------------------------------
    # LLM proposal
    # --------------------------------------------------------

    with col2:

        st.markdown(
            "### LLM Proposal"
        )

        st.metric(
            "Heating Setpoint",
            format_setpoint(
                proposed_heating
            )
        )

        st.metric(
            "Cooling Setpoint",
            format_setpoint(
                proposed_cooling
            )
        )


    # --------------------------------------------------------
    # Final approved action
    # --------------------------------------------------------

    with col3:

        st.markdown(
            "### Final Approved"
        )

        st.metric(
            "Heating Setpoint",
            format_setpoint(
                approved_heating
            )
        )

        st.metric(
            "Cooling Setpoint",
            format_setpoint(
                approved_cooling
            )
        )


    # ========================================================
    # PIPELINE SUMMARY
    # ========================================================

    st.markdown(
        "#### Control Flow"
    )


    st.code(
        (
            f"Previous HVAC     "
            f"{previous_heating} / {previous_cooling} °C\n"
            f"        |\n"
            f"        v\n"
            f"Local Qwen LLM    "
            f"{proposed_heating} / {proposed_cooling} °C\n"
            f"        |\n"
            f"        v\n"
            f"Semantic Guard\n"
            f"        |\n"
            f"        v\n"
            f"Safety Guard\n"
            f"        |\n"
            f"        v\n"
            f"Approved HVAC     "
            f"{approved_heating} / {approved_cooling} °C"
        ),
        language="text"
    )


    # ========================================================
    # AI EXPLANATION
    # ========================================================

    st.subheader(
        "AI Explanation"
    )


    reason = decision.get(
        "reason",
        "No explanation available."
    )


    energy_strategy = decision.get(
        "energy_strategy",
        "No energy strategy available."
    )


    comfort_risk = str(
        decision.get(
            "comfort_risk",
            "unknown"
        )
    ).lower()


    col1, col2 = st.columns(2)


    with col1:

        st.markdown(
            "**Decision Reason**"
        )

        st.info(
            reason
        )


    with col2:

        st.markdown(
            "**Energy Strategy**"
        )

        st.info(
            energy_strategy
        )


    # ========================================================
    # COMFORT RISK
    # ========================================================

    st.markdown(
        "#### Comfort Risk"
    )


    if comfort_risk == "low":

        st.success(
            "LOW — Current conditions are within "
            "the acceptable comfort range."
        )


    elif comfort_risk == "medium":

        st.warning(
            "MEDIUM — Conditions are approaching "
            "the comfort boundary."
        )


    elif comfort_risk == "high":

        st.error(
            "HIGH — Occupied zones are outside "
            "the desired comfort range."
        )


    else:

        st.info(
            f"Comfort risk: {comfort_risk.upper()}"
        )


    # ========================================================
    # SAFETY PIPELINE
    # ========================================================

    st.subheader(
        "AI Safety Pipeline"
    )


    semantic_modified = decision.get(
        "semantic_modified",
        False
    )


    semantic_corrections = decision.get(
        "semantic_corrections",
        []
    )


    safety_modified = decision.get(
        "safety_modified",
        False
    )


    safety_corrections = decision.get(
        "safety_corrections",
        []
    )


    col1, col2 = st.columns(2)


    # ========================================================
    # SEMANTIC GUARD
    # ========================================================

    with col1:

        st.markdown(
            "### Semantic Guard"
        )


        if semantic_modified:

            st.warning(
                "AI proposal required semantic correction."
            )


            if semantic_corrections:

                for correction in semantic_corrections:

                    st.write(
                        f"• {correction}"
                    )

            else:

                st.write(
                    "Semantic correction applied."
                )


        else:

            st.success(
                "AI proposal passed semantic validation."
            )


    # ========================================================
    # SAFETY GUARD
    # ========================================================

    with col2:

        st.markdown(
            "### Deterministic Safety Guard"
        )


        if safety_modified:

            st.warning(
                "HVAC action required safety correction."
            )


            if safety_corrections:

                for correction in safety_corrections:

                    st.write(
                        f"• {correction}"
                    )

            else:

                st.write(
                    "Safety correction applied."
                )


        else:

            st.success(
                "HVAC action passed deterministic "
                "safety validation."
            )


    # ========================================================
    # INTERVENTION SUMMARY
    # ========================================================

    st.subheader(
        "Guard Intervention Summary"
    )


    semantic_count = len(
        semantic_corrections
    )


    safety_count = len(
        safety_corrections
    )


    total_interventions = (
        semantic_count
        + safety_count
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        st.metric(
            "Semantic Corrections",
            semantic_count
        )


    with col2:

        st.metric(
            "Safety Corrections",
            safety_count
        )


    with col3:

        st.metric(
            "Total Corrections",
            total_interventions
        )


    # ========================================================
    # AI DECISION TABLE
    # ========================================================

    st.subheader(
        "HVAC Decision Comparison"
    )


    comparison_df = pd.DataFrame(
        {
            "Stage": [
                "Previous HVAC",
                "LLM Proposal",
                "Final Approved"
            ],

            "Heating Setpoint (°C)": [
                previous_heating,
                proposed_heating,
                approved_heating
            ],

            "Cooling Setpoint (°C)": [
                previous_cooling,
                proposed_cooling,
                approved_cooling
            ]
        }
    )


    st.dataframe(
        comparison_df,
        width="stretch",
        hide_index=True
    )


    # ========================================================
    # DECISION CHART
    # ========================================================

    chart_df = comparison_df.copy()

    chart_df = chart_df.set_index(
        "Stage"
    )


    st.bar_chart(
        chart_df,
        width="stretch"
    )


    # ========================================================
    # RAW DETAILS
    # ========================================================

    with st.expander(
        "View Raw AI Decision JSON"
    ):

        st.json(
            decision
        )


# ============================================================
# RAW BUILDING STATE
# ============================================================

with st.expander(
    "View Raw Building State JSON"
):

    st.json(
        state
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()


footer_col1, footer_col2 = st.columns(2)


with footer_col1:

    st.caption(
        "Autonomous AI-BMS | "
        "EnergyPlus + Local LLM Control"
    )


with footer_col2:

    st.caption(
        "Dashboard automatically refreshes every 3 seconds."
    )
# ============================================================
# FINAL PERFORMANCE EVALUATION
# ============================================================

st.divider()

st.header("7-Day Winter Performance Evaluation")

st.caption(
    "Controlled EnergyPlus validation period: January 1-7. "
    "The baseline and autonomous AI controller were evaluated "
    "over the same simulation period and weather conditions."
)

EVALUATION_DIR = (
    PROJECT_ROOT
    / "results"
    / "evaluation"
)

SUMMARY_FILE = (
    EVALUATION_DIR
    / "comparison_summary.csv"
)


# ============================================================
# LOAD EVALUATION SUMMARY
# ============================================================

@st.cache_data(ttl=5)
def load_evaluation_summary(path):

    try:

        dataframe = pd.read_csv(
            path
        )

        if dataframe.empty:
            return None

        return dataframe.iloc[0]

    except (
        FileNotFoundError,
        pd.errors.EmptyDataError,
        OSError
    ):

        return None


evaluation = load_evaluation_summary(
    SUMMARY_FILE
)


if evaluation is None:

    st.warning(
        "Performance evaluation data is not available."
    )

else:

    # ========================================================
    # VALIDATION STATUS
    # ========================================================

    st.subheader(
        "Validation Summary"
    )

    matched_records = int(
        float(
            evaluation.get(
                "matched_records",
                0
            )
        )
    )

    ai_decisions = int(
        float(
            evaluation.get(
                "ai_decisions",
                0
            )
        )
    )

    ai_comfort_violation = float(
        evaluation.get(
            "ai_comfort_violation_percent",
            0
        )
    )

    comfort_compliance = max(
        0.0,
        100.0 - ai_comfort_violation
    )

    semantic_interventions = int(
        float(
            evaluation.get(
                "semantic_interventions",
                0
            )
        )
    )

    safety_interventions = int(
        float(
            evaluation.get(
                "safety_interventions",
                0
            )
        )
    )


    validation_columns = st.columns(
        5
    )


    with validation_columns[0]:

        st.metric(
            "Matched Records",
            matched_records
        )


    with validation_columns[1]:

        st.metric(
            "AI Decisions",
            ai_decisions
        )


    with validation_columns[2]:

        st.metric(
            "Comfort Compliance",
            f"{comfort_compliance:.1f}%"
        )


    with validation_columns[3]:

        st.metric(
            "Semantic Interventions",
            semantic_interventions
        )


    with validation_columns[4]:

        st.metric(
            "Safety Interventions",
            safety_interventions
        )


    # ========================================================
    # COMFORT VALIDATION
    # ========================================================

    st.subheader(
        "Occupant Comfort Validation"
    )


    baseline_comfort_violations = int(
        float(
            evaluation.get(
                "baseline_comfort_violations",
                0
            )
        )
    )

    ai_comfort_violations = int(
        float(
            evaluation.get(
                "ai_comfort_violations",
                0
            )
        )
    )

    baseline_comfort_rate = float(
        evaluation.get(
            "baseline_comfort_violation_percent",
            0
        )
    )

    ai_comfort_rate = float(
        evaluation.get(
            "ai_comfort_violation_percent",
            0
        )
    )


    comfort_columns = st.columns(
        4
    )


    with comfort_columns[0]:

        st.metric(
            "Baseline Violations",
            baseline_comfort_violations
        )


    with comfort_columns[1]:

        st.metric(
            "AI Violations",
            ai_comfort_violations
        )


    with comfort_columns[2]:

        st.metric(
            "Baseline Compliance",
            f"{100 - baseline_comfort_rate:.1f}%"
        )


    with comfort_columns[3]:

        st.metric(
            "AI Compliance",
            f"{100 - ai_comfort_rate:.1f}%"
        )


    if ai_comfort_violations == 0:

        st.success(
            "The autonomous controller maintained "
            "100% occupied thermal comfort compliance "
            "during the 7-day validation period."
        )

    else:

        st.warning(
            "Comfort violations were detected during "
            "the validation period."
        )


    # ========================================================
    # ENERGY PERFORMANCE
    # ========================================================

    st.subheader(
        "HVAC Energy Performance"
    )


    baseline_electricity = float(
        evaluation.get(
            "baseline_hvac_electricity_kwh",
            0
        )
    )

    ai_electricity = float(
        evaluation.get(
            "ai_hvac_electricity_kwh",
            0
        )
    )

    electricity_saving = float(
        evaluation.get(
            "electricity_saving_percent",
            0
        )
    )


    baseline_gas = float(
        evaluation.get(
            "baseline_heating_gas_kwh",
            0
        )
    )

    ai_gas = float(
        evaluation.get(
            "ai_heating_gas_kwh",
            0
        )
    )


    baseline_total_energy = float(
        evaluation.get(
            "baseline_total_hvac_energy_kwh",
            0
        )
    )

    ai_total_energy = float(
        evaluation.get(
            "ai_total_hvac_energy_kwh",
            0
        )
    )

    total_energy_change = float(
        evaluation.get(
            "total_hvac_energy_saving_percent",
            0
        )
    )


    energy_columns = st.columns(
        4
    )


    with energy_columns[0]:

        st.metric(
            "Baseline HVAC",
            f"{baseline_total_energy:.2f} kWh"
        )


    with energy_columns[1]:

        st.metric(
            "AI HVAC",
            f"{ai_total_energy:.2f} kWh"
        )


    with energy_columns[2]:

        st.metric(
            "Electricity Change",
            f"{electricity_saving:.2f}%"
        )


    with energy_columns[3]:

        st.metric(
            "Total Energy Change",
            f"{total_energy_change:.2f}%"
        )


    # ========================================================
    # ENERGY COMPARISON CHART
    # ========================================================

    energy_chart = pd.DataFrame(
        {
            "Baseline": [
                baseline_electricity,
                baseline_gas,
                baseline_total_energy
            ],

            "AI Controller": [
                ai_electricity,
                ai_gas,
                ai_total_energy
            ]
        },

        index=[
            "HVAC Electricity",
            "Heating Natural Gas",
            "Total HVAC Energy"
        ]
    )


    st.bar_chart(
        energy_chart
    )


    # ========================================================
    # CARBON PERFORMANCE
    # ========================================================

    st.subheader(
        "Carbon Performance"
    )


    baseline_carbon = float(
        evaluation.get(
            "baseline_total_carbon_kg",
            0
        )
    )

    ai_carbon = float(
        evaluation.get(
            "ai_total_carbon_kg",
            0
        )
    )

    carbon_change = float(
        evaluation.get(
            "total_carbon_reduction_percent",
            0
        )
    )


    carbon_columns = st.columns(
        3
    )


    with carbon_columns[0]:

        st.metric(
            "Baseline CO2",
            f"{baseline_carbon:.2f} kg"
        )


    with carbon_columns[1]:

        st.metric(
            "AI CO2",
            f"{ai_carbon:.2f} kg"
        )


    with carbon_columns[2]:

        st.metric(
            "CO2 Change",
            f"{carbon_change:.2f}%"
        )


    carbon_chart = pd.DataFrame(
        {
            "CO2 Emissions (kg)": [
                baseline_carbon,
                ai_carbon
            ]
        },

        index=[
            "Baseline",
            "AI Controller"
        ]
    )


    st.bar_chart(
        carbon_chart
    )


    # ========================================================
    # AI GOVERNANCE
    # ========================================================

    st.subheader(
        "AI Safety & Governance"
    )


    semantic_corrections = int(
        float(
            evaluation.get(
                "semantic_corrections",
                0
            )
        )
    )

    safety_corrections = int(
        float(
            evaluation.get(
                "safety_corrections",
                0
            )
        )
    )


    governance_columns = st.columns(
        5
    )


    with governance_columns[0]:

        st.metric(
            "LLM Decisions",
            ai_decisions
        )


    with governance_columns[1]:

        st.metric(
            "Semantic Interventions",
            semantic_interventions
        )


    with governance_columns[2]:

        st.metric(
            "Semantic Corrections",
            semantic_corrections
        )


    with governance_columns[3]:

        st.metric(
            "Safety Interventions",
            safety_interventions
        )


    with governance_columns[4]:

        st.metric(
            "Safety Corrections",
            safety_corrections
        )


    st.info(
        "AI recommendations are never applied directly to "
        "the HVAC system. Every LLM decision passes through "
        "semantic validation, deterministic safety checks, "
        "and real-time comfort protection before actuation."
    )


    # ========================================================
    # GOVERNANCE CHART
    # ========================================================

    governance_chart = pd.DataFrame(
        {
            "Count": [
                ai_decisions,
                semantic_interventions,
                safety_interventions
            ]
        },

        index=[
            "AI Decisions",
            "Semantic Interventions",
            "Safety Interventions"
        ]
    )


    st.bar_chart(
        governance_chart
    )


    # ========================================================
    # EXPERIMENT INTERPRETATION
    # ========================================================

    st.subheader(
        "Validation Interpretation"
    )


    st.markdown(
        """
**Key outcome:** The autonomous AI-BMS successfully demonstrated
closed-loop LLM-based HVAC control while maintaining **100% occupied
thermal comfort compliance** during the seven-day winter validation.

The experiment also demonstrated that the governance architecture is
actively involved in control decisions. Semantic validation and the
deterministic safety layer modified AI recommendations when necessary
before HVAC actuation.

During this winter evaluation, the conservative heating recovery policy
increased natural-gas consumption relative to the baseline. This result
identifies heating-policy optimization as a future control improvement
while validating the autonomous decision, safety, comfort, logging, and
evaluation architecture.
"""
    )


# ============================================================
# SYSTEM ARCHITECTURE
# ============================================================

st.divider()

st.header(
    "Autonomous Control Architecture"
)

st.markdown(
    """
### Closed-Loop Control Pipeline

**EnergyPlus Building Simulation**

↓

**Real-Time Building State Extraction**  
Zone temperatures • Occupancy • Weather • HVAC power

↓

**Dynamic Carbon Context**  
Grid carbon intensity • Carbon level

↓

**Local Qwen LLM Supervisory Agent**  
Context-aware HVAC reasoning and setpoint recommendation

↓

**Semantic Decision Validator**  
Checks AI decisions against occupancy, comfort and carbon objectives

↓

**Deterministic Safety Guard**  
Absolute setpoint limits • Rate limits • HVAC deadband

↓

**Real-Time Comfort Guard**  
Fast deterministic protection at EnergyPlus control timesteps

↓

**Approved HVAC Setpoints**

↓

**EnergyPlus Actuators**

↓

**Operational Metrics + AI Audit Logs**

↓

**Performance Evaluation & Dashboard**
"""
)

st.caption(
    "Safety > Occupant Comfort > Energy Efficiency > Carbon Optimization"
)