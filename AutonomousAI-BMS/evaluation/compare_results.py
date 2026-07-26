from pathlib import Path
import csv
from collections import defaultdict


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_DIR = (
    PROJECT_ROOT
    / "results"
    / "evaluation"
)

BASELINE_FILE = (
    RESULTS_DIR
    / "baseline_metrics.csv"
)

AI_OPERATIONAL_FILE = (
    RESULTS_DIR
    / "ai_operational_metrics.csv"
)

AI_DECISION_FILE = (
    RESULTS_DIR
    / "ai_metrics.csv"
)

SUMMARY_FILE = (
    RESULTS_DIR
    / "comparison_summary.csv"
)


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):

    try:
        if value is None or value == "":
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):

    try:
        if value is None or value == "":
            return default

        return int(float(value))

    except (TypeError, ValueError):
        return default


def safe_bool(value):

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes"
    }


def percent_change(
    baseline,
    ai
):

    if baseline == 0:
        return 0.0

    return (
        (baseline - ai)
        / baseline
        * 100.0
    )


# ============================================================
# LOAD CSV
# ============================================================

def load_csv(path):

    if not path.exists():

        raise FileNotFoundError(
            f"Required file not found: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        return list(reader)


# ============================================================
# DEDUPLICATE BY SIMULATION TIME
# ============================================================

def deduplicate_by_simulation_time(rows):

    """
    If a simulation was accidentally appended more than once,
    keep the LAST record for each simulation_time.
    """

    records = {}

    for row in rows:

        simulation_time = (
            row.get(
                "simulation_time",
                ""
            )
            .strip()
        )

        if not simulation_time:
            continue

        records[simulation_time] = row

    return records


# ============================================================
# MATCH BASELINE AND AI
# ============================================================

def get_matched_records(
    baseline_rows,
    ai_rows
):

    baseline_map = (
        deduplicate_by_simulation_time(
            baseline_rows
        )
    )

    ai_map = (
        deduplicate_by_simulation_time(
            ai_rows
        )
    )

    common_times = sorted(
        set(baseline_map.keys())
        &
        set(ai_map.keys())
    )

    matched = []

    for simulation_time in common_times:

        matched.append(
            (
                baseline_map[simulation_time],
                ai_map[simulation_time]
            )
        )

    return (
        matched,
        baseline_map,
        ai_map
    )


# ============================================================
# OPERATIONAL METRICS
# ============================================================

def summarize_operational_rows(rows):

    summary = defaultdict(float)

    occupied_records = 0
    comfort_violations = 0

    high_carbon_records = 0

    for row in rows:

        occupancy = safe_float(
            row.get("occupancy")
        )

        # ----------------------------------------------------
        # ENERGY
        # ----------------------------------------------------

        summary[
            "hvac_electricity_kwh"
        ] += safe_float(
            row.get(
                "hvac_electricity_kwh"
            )
        )

        summary[
            "cooling_electricity_kwh"
        ] += safe_float(
            row.get(
                "cooling_electricity_kwh"
            )
        )

        summary[
            "fans_electricity_kwh"
        ] += safe_float(
            row.get(
                "fans_electricity_kwh"
            )
        )

        summary[
            "pumps_electricity_kwh"
        ] += safe_float(
            row.get(
                "pumps_electricity_kwh"
            )
        )

        summary[
            "heating_natural_gas_kwh"
        ] += safe_float(
            row.get(
                "heating_natural_gas_kwh"
            )
        )

        summary[
            "heating_demand_kwh"
        ] += safe_float(
            row.get(
                "heating_demand_kwh"
            )
        )

        summary[
            "cooling_demand_kwh"
        ] += safe_float(
            row.get(
                "cooling_demand_kwh"
            )
        )

        summary[
            "total_hvac_site_energy_kwh"
        ] += safe_float(
            row.get(
                "total_hvac_site_energy_kwh"
            )
        )

        # ----------------------------------------------------
        # CARBON
        # ----------------------------------------------------

        summary[
            "electricity_carbon_kg"
        ] += safe_float(
            row.get(
                "electricity_carbon_kg"
            )
        )

        summary[
            "gas_carbon_kg"
        ] += safe_float(
            row.get(
                "gas_carbon_kg"
            )
        )

        summary[
            "total_hvac_carbon_kg"
        ] += safe_float(
            row.get(
                "total_hvac_carbon_kg"
            )
        )

        # ----------------------------------------------------
        # COMFORT
        # ----------------------------------------------------

        if occupancy > 0:

            occupied_records += 1

            comfort_violations += (
                safe_int(
                    row.get(
                        "comfort_violation"
                    )
                )
            )

        # ----------------------------------------------------
        # HIGH CARBON PERIOD
        # ----------------------------------------------------

        carbon_level = (
            row.get(
                "carbon_level",
                ""
            )
            .strip()
            .lower()
        )

        if carbon_level == "high":

            high_carbon_records += 1

            summary[
                "high_carbon_electricity_kwh"
            ] += safe_float(
                row.get(
                    "hvac_electricity_kwh"
                )
            )

            summary[
                "high_carbon_gas_kwh"
            ] += safe_float(
                row.get(
                    "heating_natural_gas_kwh"
                )
            )

            summary[
                "high_carbon_site_energy_kwh"
            ] += safe_float(
                row.get(
                    "total_hvac_site_energy_kwh"
                )
            )

            summary[
                "high_carbon_emissions_kg"
            ] += safe_float(
                row.get(
                    "total_hvac_carbon_kg"
                )
            )

    summary[
        "occupied_records"
    ] = occupied_records

    summary[
        "comfort_violations"
    ] = comfort_violations

    summary[
        "high_carbon_records"
    ] = high_carbon_records

    if occupied_records > 0:

        summary[
            "comfort_violation_percent"
        ] = (
            comfort_violations
            / occupied_records
            * 100.0
        )

    else:

        summary[
            "comfort_violation_percent"
        ] = 0.0

    return summary


# ============================================================
# AI GOVERNANCE METRICS
# ============================================================

def summarize_ai_decisions(rows):

    if not rows:

        return {
            "ai_decisions": 0,
            "semantic_interventions": 0,
            "semantic_corrections": 0,
            "safety_interventions": 0,
            "safety_corrections": 0
        }

    # Keep only latest record for every AI call.
    calls = {}

    for row in rows:

        call = row.get(
            "ai_call"
        )

        if call is None or call == "":
            continue

        calls[str(call)] = row

    semantic_interventions = 0
    semantic_corrections = 0

    safety_interventions = 0
    safety_corrections = 0

    for row in calls.values():

        if safe_bool(
            row.get(
                "semantic_modified"
            )
        ):

            semantic_interventions += 1

        semantic_corrections += (
            safe_int(
                row.get(
                    "semantic_correction_count"
                )
            )
        )

        if safe_bool(
            row.get(
                "safety_modified"
            )
        ):

            safety_interventions += 1

        safety_corrections += (
            safe_int(
                row.get(
                    "safety_correction_count"
                )
            )
        )

    return {

        "ai_decisions":
            len(calls),

        "semantic_interventions":
            semantic_interventions,

        "semantic_corrections":
            semantic_corrections,

        "safety_interventions":
            safety_interventions,

        "safety_corrections":
            safety_corrections
    }


# ============================================================
# MAIN COMPARISON
# ============================================================

def compare_results():

    print()
    print("=" * 64)
    print("      AUTONOMOUS AI-BMS FINAL PERFORMANCE EVALUATION")
    print("=" * 64)
    print()

    # --------------------------------------------------------
    # LOAD FILES
    # --------------------------------------------------------

    baseline_rows = load_csv(
        BASELINE_FILE
    )

    ai_rows = load_csv(
        AI_OPERATIONAL_FILE
    )

    if AI_DECISION_FILE.exists():

        ai_decision_rows = load_csv(
            AI_DECISION_FILE
        )

    else:

        ai_decision_rows = []

    # --------------------------------------------------------
    # MATCH TIMESTEPS
    # --------------------------------------------------------

    (
        matched,
        baseline_map,
        ai_map
    ) = get_matched_records(
        baseline_rows,
        ai_rows
    )

    if not matched:

        raise RuntimeError(
            "No matching simulation_time records "
            "between baseline and AI files."
        )

    matched_baseline = [
        pair[0]
        for pair in matched
    ]

    matched_ai = [
        pair[1]
        for pair in matched
    ]

    print(
        f"Baseline unique records : "
        f"{len(baseline_map)}"
    )

    print(
        f"AI unique records       : "
        f"{len(ai_map)}"
    )

    print(
        f"Matched records         : "
        f"{len(matched)}"
    )

    print()

    # --------------------------------------------------------
    # SUMMARIZE
    # --------------------------------------------------------

    baseline = (
        summarize_operational_rows(
            matched_baseline
        )
    )

    ai = (
        summarize_operational_rows(
            matched_ai
        )
    )

    governance = (
        summarize_ai_decisions(
            ai_decision_rows
        )
    )

    # ========================================================
    # ENERGY RESULTS
    # ========================================================

    electricity_saving = (
        baseline[
            "hvac_electricity_kwh"
        ]
        -
        ai[
            "hvac_electricity_kwh"
        ]
    )

    gas_saving = (
        baseline[
            "heating_natural_gas_kwh"
        ]
        -
        ai[
            "heating_natural_gas_kwh"
        ]
    )

    site_energy_saving = (
        baseline[
            "total_hvac_site_energy_kwh"
        ]
        -
        ai[
            "total_hvac_site_energy_kwh"
        ]
    )

    electricity_saving_percent = (
        percent_change(
            baseline[
                "hvac_electricity_kwh"
            ],
            ai[
                "hvac_electricity_kwh"
            ]
        )
    )

    gas_saving_percent = (
        percent_change(
            baseline[
                "heating_natural_gas_kwh"
            ],
            ai[
                "heating_natural_gas_kwh"
            ]
        )
    )

    site_energy_saving_percent = (
        percent_change(
            baseline[
                "total_hvac_site_energy_kwh"
            ],
            ai[
                "total_hvac_site_energy_kwh"
            ]
        )
    )

    # ========================================================
    # CARBON RESULTS
    # ========================================================

    electricity_carbon_reduction = (
        baseline[
            "electricity_carbon_kg"
        ]
        -
        ai[
            "electricity_carbon_kg"
        ]
    )

    gas_carbon_reduction = (
        baseline[
            "gas_carbon_kg"
        ]
        -
        ai[
            "gas_carbon_kg"
        ]
    )

    total_carbon_reduction = (
        baseline[
            "total_hvac_carbon_kg"
        ]
        -
        ai[
            "total_hvac_carbon_kg"
        ]
    )

    total_carbon_reduction_percent = (
        percent_change(
            baseline[
                "total_hvac_carbon_kg"
            ],
            ai[
                "total_hvac_carbon_kg"
            ]
        )
    )

    # ========================================================
    # COMFORT
    # ========================================================

    comfort_improvement = (
        baseline[
            "comfort_violation_percent"
        ]
        -
        ai[
            "comfort_violation_percent"
        ]
    )

    # ========================================================
    # HIGH CARBON PERFORMANCE
    # ========================================================

    high_carbon_energy_reduction = (
        percent_change(
            baseline[
                "high_carbon_site_energy_kwh"
            ],
            ai[
                "high_carbon_site_energy_kwh"
            ]
        )
    )

    high_carbon_emission_reduction = (
        percent_change(
            baseline[
                "high_carbon_emissions_kg"
            ],
            ai[
                "high_carbon_emissions_kg"
            ]
        )
    )

    # ========================================================
    # PRINT ENERGY
    # ========================================================

    print("=" * 64)
    print("ENERGY PERFORMANCE")
    print("=" * 64)

    print(
        f"Baseline HVAC electricity : "
        f"{baseline['hvac_electricity_kwh']:.3f} kWh"
    )

    print(
        f"AI HVAC electricity       : "
        f"{ai['hvac_electricity_kwh']:.3f} kWh"
    )

    print(
        f"Electricity saving        : "
        f"{electricity_saving:.3f} kWh "
        f"({electricity_saving_percent:.2f}%)"
    )

    print()

    print(
        f"Baseline heating gas      : "
        f"{baseline['heating_natural_gas_kwh']:.3f} kWh"
    )

    print(
        f"AI heating gas            : "
        f"{ai['heating_natural_gas_kwh']:.3f} kWh"
    )

    print(
        f"Gas saving                : "
        f"{gas_saving:.3f} kWh "
        f"({gas_saving_percent:.2f}%)"
    )

    print()

    print(
        f"Baseline total HVAC energy: "
        f"{baseline['total_hvac_site_energy_kwh']:.3f} kWh"
    )

    print(
        f"AI total HVAC energy      : "
        f"{ai['total_hvac_site_energy_kwh']:.3f} kWh"
    )

    print(
        f"Total HVAC energy saving  : "
        f"{site_energy_saving:.3f} kWh "
        f"({site_energy_saving_percent:.2f}%)"
    )

    # ========================================================
    # CARBON
    # ========================================================

    print()
    print("=" * 64)
    print("CARBON PERFORMANCE")
    print("=" * 64)

    print(
        f"Baseline electricity CO2 : "
        f"{baseline['electricity_carbon_kg']:.3f} kg"
    )

    print(
        f"AI electricity CO2       : "
        f"{ai['electricity_carbon_kg']:.3f} kg"
    )

    print(
        f"Electricity CO2 reduction: "
        f"{electricity_carbon_reduction:.3f} kg"
    )

    print()

    print(
        f"Baseline gas CO2         : "
        f"{baseline['gas_carbon_kg']:.3f} kg"
    )

    print(
        f"AI gas CO2               : "
        f"{ai['gas_carbon_kg']:.3f} kg"
    )

    print(
        f"Gas CO2 reduction        : "
        f"{gas_carbon_reduction:.3f} kg"
    )

    print()

    print(
        f"Baseline total HVAC CO2  : "
        f"{baseline['total_hvac_carbon_kg']:.3f} kg"
    )

    print(
        f"AI total HVAC CO2        : "
        f"{ai['total_hvac_carbon_kg']:.3f} kg"
    )

    print(
        f"Total CO2 reduction      : "
        f"{total_carbon_reduction:.3f} kg "
        f"({total_carbon_reduction_percent:.2f}%)"
    )

    # ========================================================
    # COMFORT
    # ========================================================

    print()
    print("=" * 64)
    print("OCCUPANT COMFORT")
    print("=" * 64)

    print(
        f"Baseline occupied records : "
        f"{int(baseline['occupied_records'])}"
    )

    print(
        f"AI occupied records       : "
        f"{int(ai['occupied_records'])}"
    )

    print(
        f"Baseline violations       : "
        f"{int(baseline['comfort_violations'])}"
    )

    print(
        f"AI violations             : "
        f"{int(ai['comfort_violations'])}"
    )

    print(
        f"Baseline violation rate   : "
        f"{baseline['comfort_violation_percent']:.2f}%"
    )

    print(
        f"AI violation rate         : "
        f"{ai['comfort_violation_percent']:.2f}%"
    )

    print(
        f"Comfort improvement       : "
        f"{comfort_improvement:.2f} percentage points"
    )

    # ========================================================
    # HIGH CARBON PERIOD
    # ========================================================

    print()
    print("=" * 64)
    print("HIGH-CARBON PERIOD PERFORMANCE")
    print("=" * 64)

    print(
        f"High-carbon records       : "
        f"{int(ai['high_carbon_records'])}"
    )

    print(
        f"Baseline high-carbon HVAC : "
        f"{baseline['high_carbon_site_energy_kwh']:.3f} kWh"
    )

    print(
        f"AI high-carbon HVAC       : "
        f"{ai['high_carbon_site_energy_kwh']:.3f} kWh"
    )

    print(
        f"High-carbon energy change : "
        f"{high_carbon_energy_reduction:.2f}%"
    )

    print()

    print(
        f"Baseline high-carbon CO2  : "
        f"{baseline['high_carbon_emissions_kg']:.3f} kg"
    )

    print(
        f"AI high-carbon CO2        : "
        f"{ai['high_carbon_emissions_kg']:.3f} kg"
    )

    print(
        f"High-carbon CO2 reduction : "
        f"{high_carbon_emission_reduction:.2f}%"
    )

    # ========================================================
    # AI GOVERNANCE
    # ========================================================

    print()
    print("=" * 64)
    print("AI SAFETY & GOVERNANCE")
    print("=" * 64)

    print(
        f"AI decisions              : "
        f"{governance['ai_decisions']}"
    )

    print(
        f"Semantic interventions    : "
        f"{governance['semantic_interventions']}"
    )

    print(
        f"Semantic corrections      : "
        f"{governance['semantic_corrections']}"
    )

    print(
        f"Safety interventions      : "
        f"{governance['safety_interventions']}"
    )

    print(
        f"Safety corrections        : "
        f"{governance['safety_corrections']}"
    )

    # ========================================================
    # CREATE SUMMARY CSV
    # ========================================================

    result = {

        "matched_records":
            len(matched),

        "baseline_hvac_electricity_kwh":
            baseline[
                "hvac_electricity_kwh"
            ],

        "ai_hvac_electricity_kwh":
            ai[
                "hvac_electricity_kwh"
            ],

        "electricity_saving_kwh":
            electricity_saving,

        "electricity_saving_percent":
            electricity_saving_percent,

        "baseline_heating_gas_kwh":
            baseline[
                "heating_natural_gas_kwh"
            ],

        "ai_heating_gas_kwh":
            ai[
                "heating_natural_gas_kwh"
            ],

        "gas_saving_kwh":
            gas_saving,

        "gas_saving_percent":
            gas_saving_percent,

        "baseline_total_hvac_energy_kwh":
            baseline[
                "total_hvac_site_energy_kwh"
            ],

        "ai_total_hvac_energy_kwh":
            ai[
                "total_hvac_site_energy_kwh"
            ],

        "total_hvac_energy_saving_kwh":
            site_energy_saving,

        "total_hvac_energy_saving_percent":
            site_energy_saving_percent,

        "baseline_total_carbon_kg":
            baseline[
                "total_hvac_carbon_kg"
            ],

        "ai_total_carbon_kg":
            ai[
                "total_hvac_carbon_kg"
            ],

        "total_carbon_reduction_kg":
            total_carbon_reduction,

        "total_carbon_reduction_percent":
            total_carbon_reduction_percent,

        "baseline_comfort_violations":
            int(
                baseline[
                    "comfort_violations"
                ]
            ),

        "ai_comfort_violations":
            int(
                ai[
                    "comfort_violations"
                ]
            ),

        "baseline_comfort_violation_percent":
            baseline[
                "comfort_violation_percent"
            ],

        "ai_comfort_violation_percent":
            ai[
                "comfort_violation_percent"
            ],

        "comfort_improvement_percentage_points":
            comfort_improvement,

        "baseline_high_carbon_energy_kwh":
            baseline[
                "high_carbon_site_energy_kwh"
            ],

        "ai_high_carbon_energy_kwh":
            ai[
                "high_carbon_site_energy_kwh"
            ],

        "high_carbon_energy_reduction_percent":
            high_carbon_energy_reduction,

        "baseline_high_carbon_emissions_kg":
            baseline[
                "high_carbon_emissions_kg"
            ],

        "ai_high_carbon_emissions_kg":
            ai[
                "high_carbon_emissions_kg"
            ],

        "high_carbon_emission_reduction_percent":
            high_carbon_emission_reduction,

        "ai_decisions":
            governance[
                "ai_decisions"
            ],

        "semantic_interventions":
            governance[
                "semantic_interventions"
            ],

        "semantic_corrections":
            governance[
                "semantic_corrections"
            ],

        "safety_interventions":
            governance[
                "safety_interventions"
            ],

        "safety_corrections":
            governance[
                "safety_corrections"
            ]
    }

    with open(
        SUMMARY_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(
                result.keys()
            )
        )

        writer.writeheader()

        writer.writerow(
            result
        )

    print()
    print("=" * 64)

    print(
        "Comparison summary saved to:"
    )

    print(
        SUMMARY_FILE
    )

    print("=" * 64)
    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    compare_results()