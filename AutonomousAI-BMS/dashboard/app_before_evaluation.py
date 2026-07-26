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