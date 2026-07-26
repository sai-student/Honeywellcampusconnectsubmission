# Autonomous AI-Powered Building Management System (AI-BMS)
## PoC Demonstration Video
### [▶ Watch the PoC Demonstration Video](Demovideo.mp4)
### 3-Minute Autonomous AI-BMS Closed-Loop Demonstration

The demonstration shows the complete autonomous control loop:

**EnergyPlus → Building State Extraction → Carbon Context → Local Qwen LLM → Semantic Validator → Safety Guard → Real-Time Comfort Guard → HVAC Actuators → EnergyPlus**

The video demonstrates:

- Live building-state extraction from EnergyPlus
- Data transfer from EnergyPlus to the AI controller
- Local Qwen LLM supervisory decision-making
- AI-generated HVAC heating and cooling setpoints
- Semantic validation
- Deterministic safety validation
- Real-time occupant comfort protection
- Automatic application of approved setpoints
- Closed-loop feedback to EnergyPlus
- Live dashboard visualization

## Honeywell Campus Connect – Proof of Concept Submission

An autonomous, safety-aware and carbon-aware Building Management System that integrates **EnergyPlus 26.1** with a **locally running Qwen Large Language Model (LLM)** to make supervisory HVAC control decisions based on live simulated building conditions.

The system implements a closed-loop control architecture:

**EnergyPlus → Building State Extraction → Carbon Context → Qwen LLM → Semantic Validator → Safety Guard → Real-Time Comfort Guard → HVAC Actuators → EnergyPlus**

The objective is to investigate how an LLM-based supervisory controller can interact with a realistic building digital twin while deterministic control layers protect occupant comfort and HVAC safety.

---

# 1. Project Overview

Traditional Building Management Systems generally rely on fixed schedules, rule-based controllers and predefined HVAC setpoints.

This project explores a different architecture in which a local Large Language Model acts as a **supervisory optimization agent**.

During an EnergyPlus simulation, the system extracts live information including:

- Zone temperatures
- Zone occupancy
- Outdoor temperature
- Current heating setpoint
- Current cooling setpoint
- HVAC power
- Electricity consumption
- Natural-gas consumption
- Heating demand
- Cooling demand
- Carbon intensity

This information is converted into structured context for the local Qwen LLM.

The LLM proposes new heating and cooling setpoints together with:

- Decision reasoning
- Energy strategy
- Comfort-risk assessment

The LLM is **not allowed to directly control the simulated HVAC system**.

Every proposal must pass through deterministic validation and safety layers before it can be applied to EnergyPlus.

---

# 2. System Architecture

The system follows the closed-loop architecture shown below:

```text
                  ┌─────────────────────────────┐
                  │      EnergyPlus 26.1        │
                  │        Digital Twin         │
                  └──────────────┬──────────────┘
                                 │
                                 ▼
                  ┌─────────────────────────────┐
                  │   Building State Extraction │
                  │                             │
                  │ • Occupancy                 │
                  │ • Zone temperatures         │
                  │ • Outdoor temperature       │
                  │ • HVAC power                │
                  │ • Current setpoints         │
                  │ • Energy / demand metrics   │
                  └──────────────┬──────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
          ┌──────────────────┐       ┌──────────────────┐
          │ Carbon Context   │       │ Telemetry Logger │
          │                  │       │                  │
          │ Low / Moderate / │       │ CSV / JSON       │
          │ High Carbon      │       │ Dashboard        │
          └────────┬─────────┘       └──────────────────┘
                   │
                   ▼
          ┌──────────────────────────┐
          │     Local Qwen LLM       │
          │ Supervisory AI Controller│
          └────────────┬─────────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │ Structured JSON Proposal │
          │                          │
          │ Heating Setpoint         │
          │ Cooling Setpoint         │
          │ Reason                   │
          │ Energy Strategy          │
          │ Comfort Risk             │
          └────────────┬─────────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │    Semantic Validator    │
          └────────────┬─────────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │       Safety Guard       │
          └────────────┬─────────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │ Real-Time Comfort Guard  │
          └────────────┬─────────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │ EnergyPlus HVAC Actuators│
          │                          │
          │ Heating Schedule         │
          │ Cooling Schedule         │
          └────────────┬─────────────┘
                       │
                       │ Feedback
                       └──────────────► EnergyPlus
```

This creates a continuous autonomous feedback loop.

---

# 3. EnergyPlus Digital Twin

**EnergyPlus 26.1** is used as the building simulation and digital-twin environment.

The building model contains multiple thermal zones with:

- HVAC systems
- Occupancy schedules
- Heating schedules
- Cooling schedules
- Weather conditions
- Internal loads
- Energy meters

The EnergyPlus Python API provides runtime access to simulation variables and actuators.

The controller reads building conditions while the simulation is running rather than relying only on post-processing.

---

# 4. Building State Extraction

At runtime, the controller extracts information from EnergyPlus including:

```text
Simulation Time
Outdoor Temperature
Total Occupancy

Zone Temperatures
Zone Occupancies

Minimum Occupied Temperature
Maximum Occupied Temperature
Average Occupied Temperature

Current Heating Setpoint
Current Cooling Setpoint

HVAC Power
Electricity Consumption
Natural Gas Consumption

Heating Demand
Cooling Demand
```

This information forms the current state observed by the autonomous controller.

---

# 5. Local Qwen LLM Controller

A locally running **Qwen LLM** acts as the supervisory decision-making component.

Running the model locally provides:

- Local inference
- No dependency on an external cloud LLM during control
- Greater control over the inference pipeline
- Reproducible prompt engineering
- Reduced external service dependency

The LLM receives a structured description of the current building state.

It returns JSON in the following form:

```json
{
    "heating": 20.0,
    "cooling": 25.0,
    "reason": "Explanation of the HVAC decision",
    "energy_strategy": "Description of the energy/carbon strategy",
    "comfort_risk": "low"
}
```

Structured output makes the LLM response easier to validate programmatically.

---

# 6. Prompt Engineering Strategy

The LLM is instructed to optimize several objectives in priority order.

## Priority 1 – Safety

Unsafe HVAC conditions must never intentionally be created.

## Priority 2 – Occupant Comfort

When occupied, the target comfort range is:

```text
20°C <= occupied-zone temperature <= 26°C
```

## Priority 3 – Energy Efficiency

HVAC operation should be reduced when it is unnecessary.

## Priority 4 – Carbon Awareness

Carbon reduction is considered whenever safety and comfort permit.

The prompt also defines hard operating expectations such as:

```text
18°C <= Heating Setpoint <= 22°C

24°C <= Cooling Setpoint <= 29°C
```

and requires a sufficient heating/cooling deadband.

When the building is unoccupied, the controller is encouraged to use a wider deadband where appropriate.

---

# 7. Semantic Validator

LLM output can be syntactically valid while still being contextually inappropriate.

Therefore, the first post-LLM layer is a **Semantic Validator**.

It checks whether the proposed action makes sense given:

- Occupancy
- Current zone temperatures
- Current HVAC setpoints
- Heating/cooling requirements
- LLM explanation
- Energy strategy
- Comfort conditions

For example, if occupied zones are approaching a temperature limit and an LLM recommendation would unnecessarily worsen comfort, the semantic layer can correct the recommendation.

All such interventions are recorded for evaluation.

---

# 8. Deterministic Safety Guard

After semantic validation, the proposal enters a deterministic Safety Guard.

Unlike the LLM, this layer is implemented using explicit programmatic constraints.

It protects against:

- Heating setpoints outside permitted limits
- Cooling setpoints outside permitted limits
- Insufficient heating/cooling deadband
- Excessively large setpoint changes
- Invalid or extreme LLM recommendations

Only a validated safe action can proceed to EnergyPlus.

This design ensures that the LLM is a **supervisory intelligence layer rather than an unrestricted actuator controller**.

---

# 9. Real-Time Comfort Guard

LLM inference is significantly slower than deterministic control logic.

The architecture therefore includes a separate **Real-Time Comfort Guard**.

The supervisory LLM can operate at a relatively slow simulation interval, while the comfort guard operates locally at EnergyPlus callbacks.

The guard monitors:

```text
Occupancy
Minimum occupied temperature
Maximum occupied temperature
Heating setpoint
Cooling setpoint
```

If occupied-zone comfort becomes threatened, the guard can modify the setpoints without waiting for another LLM decision.

This decouples:

**Slow AI reasoning**

from

**Fast safety-critical comfort protection**

and is an important latency-management mechanism in the architecture.

---

# 10. Automatic EnergyPlus Control

After validation, the approved HVAC values are automatically written back into the running EnergyPlus model through the EnergyPlus Python API.

Conceptually:

```python
api.exchange.set_actuator_value(
    state,
    heating_actuator,
    approved_heating_setpoint
)

api.exchange.set_actuator_value(
    state,
    cooling_actuator,
    approved_cooling_setpoint
)
```

The relevant actuators control the EnergyPlus heating and cooling schedules.

Therefore, the PoC demonstrates an actual closed loop:

```text
EnergyPlus
    ↓
Read Building State
    ↓
LLM Decision
    ↓
Semantic Validation
    ↓
Safety Validation
    ↓
Real-Time Comfort Protection
    ↓
Apply HVAC Setpoints
    ↓
EnergyPlus Continues
    ↓
New Building State
    ↓
Repeat
```

No manual setpoint modification is required during this loop.

---

# 11. Fail-Safe Architecture

The LLM is not assumed to be perfectly reliable.

The controller includes exception handling and fail-safe behavior.

If AI inference fails, produces unusable output or causes an exception:

1. The AI failure is recorded.
2. The invalid recommendation is not applied.
3. Previous validated safe setpoints are retained.
4. EnergyPlus continues running.

This prevents an AI failure from directly producing an unsafe HVAC command.

---

# 12. Carbon-Aware HVAC Control

The controller also receives a carbon-intensity signal.

Carbon conditions are classified as:

```text
LOW
MODERATE
HIGH
```

The LLM can use this context when deciding whether HVAC demand can safely be reduced.

The control priority remains:

```text
Safety
   ↓
Occupant Comfort
   ↓
Energy Efficiency
   ↓
Carbon Optimization
```

Therefore, carbon reduction cannot intentionally override safety or occupant comfort.

---

# 13. Telemetry and Logging

A dedicated telemetry pipeline records both operational and AI-governance information.

## Operational Metrics

Examples include:

```text
Simulation Time
Outdoor Temperature
Occupancy
Zone Temperatures
Heating Setpoint
Cooling Setpoint
HVAC Power
Electricity Consumption
Natural Gas Consumption
Heating Demand
Cooling Demand
Carbon Intensity
Comfort Violations
```

## AI Governance Metrics

The system also records:

```text
AI Calls
AI Failures
Semantic Interventions
Semantic Corrections
Safety Interventions
Safety Corrections
Real-Time Comfort Guard Interventions
```

This allows the system to be evaluated not only on energy performance but also on AI behavior and safety-layer activity.

---

# 14. Handling Lengthy Simulation Logs

EnergyPlus simulations can generate very large amounts of output.

Sending complete simulation logs to the LLM would:

- Increase prompt size
- Increase inference latency
- Add irrelevant information
- Reduce control efficiency

The architecture therefore uses **state abstraction**.

Instead of sending raw EnergyPlus logs, the controller extracts only decision-relevant features.

For example:

```text
Outdoor Temperature: -4.0°C
Occupancy: 42
Average Occupied Temperature: 23.8°C
Minimum Occupied Temperature: 22.1°C
Maximum Occupied Temperature: 25.4°C
Heating Setpoint: 20.0°C
Cooling Setpoint: 25.0°C
Carbon Level: Low
```

This compact representation is sent to the LLM.

Detailed simulation data remains available separately for:

- Evaluation
- Debugging
- Telemetry
- Visualization

This reduces prompt size and improves inference efficiency.

---

# 15. Prompt-Latency Management

Several techniques are used to manage LLM latency.

### Supervisory AI Control

The LLM does not need to execute at every EnergyPlus timestep.

It operates as a supervisory optimizer.

### Fast Local Safety Layers

Semantic, safety and comfort logic execute locally in Python.

### Real-Time Comfort Protection

Comfort protection does not wait for an LLM response.

### State Compression

Only relevant building-state variables are included in the LLM prompt.

### Local Inference

Qwen is executed locally, removing external API/network latency from the primary AI-control path.

Together these create a hybrid architecture:

```text
LLM = slow intelligent supervisory reasoning

Python Guards = fast deterministic protection

EnergyPlus = physical/digital building dynamics
```

---

# 16. Live Dashboard

A Streamlit dashboard provides real-time visibility into the autonomous controller.

The dashboard displays information such as:

- System status
- Simulation time
- Occupancy
- Outdoor temperature
- HVAC power
- Carbon intensity
- Occupied-zone temperatures
- Current HVAC setpoints
- AI building context
- LLM proposal
- Final approved action
- AI reasoning
- Energy strategy
- Comfort risk
- Semantic corrections
- Safety corrections
- Guard intervention statistics

The dashboard automatically refreshes while the simulation is running.

---

# 17. Evaluation Framework

The project contains a separate evaluation pipeline that compares the AI-controlled simulation against the baseline simulation.

Metrics include:

## Energy

- HVAC electricity
- Heating natural gas
- Total HVAC site energy

## Carbon

- Electricity-related CO₂
- Gas-related CO₂
- Total HVAC CO₂
- High-carbon-period performance

## Comfort

- Occupied records
- Comfort violations
- Comfort violation rate

## AI Governance

- AI decisions
- Semantic interventions
- Semantic corrections
- Safety interventions
- Safety corrections

This provides both performance evaluation and AI-governance evaluation.

---

# 18. Seven-Day PoC Evaluation

For the final rapid PoC evaluation, the EnergyPlus RunPeriod was configured for:

```text
January 1 → January 7
```

The comparison contained:

```text
Baseline unique records : 168
AI unique records       : 168
Matched records         : 161
```

## Comfort Result

```text
Baseline comfort violations : 0
AI comfort violations       : 0

Baseline violation rate : 0.00%
AI violation rate       : 0.00%
```

Therefore, the evaluated seven-day run maintained the baseline comfort-violation rate.

## AI Governance Activity

During this run:

```text
AI Decisions           : 28
Semantic Interventions : 15
Semantic Corrections   : 19
Safety Interventions   : 5
Safety Corrections     : 5
```

These results demonstrate that the safety architecture actively intercepted and modified AI decisions rather than blindly forwarding LLM output to EnergyPlus.

## Energy/Carbon Result

The seven-day experiment did **not** demonstrate an energy or carbon reduction relative to the baseline.

The measured total HVAC energy and associated emissions were higher than the baseline during this test configuration.

This result is retained transparently because the purpose of the PoC is also to evaluate the limitations of autonomous LLM-based building control.

The experiment demonstrates a functional and safety-governed autonomous control architecture, while further optimization of the supervisory control policy is required to achieve consistent energy and carbon savings.

---

# 19. Repository Structure

```text
AutonomousAI-BMS/
│
├── ai_engine/
│   ├── decision_engine.py
│   ├── llm_client.py
│   └── ...
│
├── building/
│   └── models/
│       ├── 5ZoneAI.idf
│       ├── 5ZoneAI_full_year.idf
│       └── ...
│
├── carbon/
│   ├── carbon_model.py
│   └── ...
│
├── controller/
│   ├── safety_guard.py
│   └── ...
│
├── dashboard/
│   └── app.py
│
├── data/
│   ├── live_building_state.json
│   └── live_ai_decision.json
│
├── evaluation/
│   ├── compare_results.py
│   └── ...
│
├── results/
│   └── evaluation/
│       ├── baseline_metrics.csv
│       ├── ai_metrics.csv
│       ├── ai_operational_metrics.csv
│       └── comparison_summary.csv
│
├── simulation/
│   ├── run_ai_control.py
│   ├── run_baseline.py
│   ├── run_controlled.py
│   ├── run_dual_control.py
│   └── ...
│
└── requirements.txt
```

The Honeywell submission repository additionally contains the project documentation, presentation and PoC demonstration video.

---

# 20. Installation

## Prerequisites

Install:

- Python 3.x
- EnergyPlus 26.1
- Local Qwen-compatible inference environment
- Streamlit
- Required Python dependencies

Clone the repository:

```bash
git clone https://github.com/sai-student/Honeywellcampusconnectsubmission.git
```

Enter the project:

```bash
cd Honeywellcampusconnectsubmission/AutonomousAI-BMS
```

Create a virtual environment:

### Windows

```powershell
python -m venv venv_ai
.\venv_ai\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

---

# 21. Running the Baseline Simulation

Activate the environment:

```powershell
.\venv_ai\Scripts\Activate.ps1
```

Run:

```powershell
python simulation\run_baseline.py
```

The baseline simulation provides the reference against which the AI-controlled system is evaluated.

---

# 22. Running the Autonomous AI Controller

Run:

```powershell
python simulation\run_ai_control.py
```

During execution, the terminal reports the enabled components, including:

```text
Controller      : Local Qwen LLM
Semantic Guard  : ENABLED
Safety Guard    : ENABLED
Real-time Guard : ENABLED
Fail-safe       : ENABLED
Carbon-aware    : ENABLED
Dynamic Carbon  : ENABLED
Live State      : ENABLED
AI Decision Feed: ENABLED
AI Metrics      : ENABLED
Operational Data: ENABLED
```

The controller then executes the EnergyPlus–AI closed loop.

---

# 23. Running the Dashboard

Open another terminal.

Activate the environment:

```powershell
.\venv_ai\Scripts\Activate.ps1
```

Run:

```powershell
streamlit run dashboard\app.py
```

Open the Streamlit URL displayed in the terminal.

The dashboard reads the live building and AI-decision state generated by the controller.

---

# 24. Running Evaluation

After baseline and AI simulations have generated their metrics:

```powershell
python evaluation\compare_results.py
```

The evaluation produces a summary under:

```text
results/evaluation/comparison_summary.csv
```

---

# 25. Proof-of-Concept Demonstration

The PoC video demonstrates the complete control loop:

```text
EnergyPlus
    ↓
Live Building Data
    ↓
Local Qwen LLM
    ↓
Structured HVAC Proposal
    ↓
Semantic Validator
    ↓
Safety Guard
    ↓
Real-Time Comfort Guard
    ↓
Approved HVAC Action
    ↓
EnergyPlus Actuator Update
    ↓
Updated Building State
```

The key objective of the demonstration is to show that building information moves from EnergyPlus to the AI controller and that validated control actions are automatically written back into the simulation without manual HVAC setpoint changes.

---

# 26. Building Models

EnergyPlus building models are included as `.idf` files under:

```text
building/models/
```

The repository contains the model used for the AI-controlled evaluation as well as preserved building-model versions used during development/evaluation.

The AI does not generate a new `.idf` file for every decision.

Instead, runtime HVAC modifications are applied dynamically using the **EnergyPlus Python API actuator interface**.

This allows setpoints to change while the EnergyPlus simulation is running.

---

# 27. Key Design Principles

The project follows five primary design principles:

### 1. LLMs should not directly control safety-critical actuators

All AI output passes through deterministic validation.

### 2. AI reasoning and real-time protection should be separated

The LLM performs supervisory reasoning while local guards provide fast protection.

### 3. Building state should be abstracted before prompting

Decision-relevant state is sent to the LLM rather than lengthy raw simulation logs.

### 4. AI behavior should be observable

Raw decisions, corrections, interventions and final actions are logged.

### 5. Experimental results should remain transparent

The PoC reports both successful behavior, such as maintained comfort and active safety interventions, and areas requiring further optimization, such as energy and carbon performance.

---

# 28. Future Improvements

Potential future work includes:

- Model Predictive Control integration
- Reinforcement-learning-assisted setpoint optimization
- Weather forecasting
- Occupancy forecasting
- Dynamic electricity pricing
- Real-time grid carbon APIs
- Adaptive AI decision intervals
- LLM decision caching
- Multi-agent HVAC control
- Zone-level independent setpoint optimization
- Historical-state summarization
- Predictive comfort models
- Automated prompt optimization
- Additional EnergyPlus building models
- Longer controlled experiments
- Hardware BMS integration using BACnet/Modbus
- Automated rollback strategies
- Human operator approval modes

A particularly important next step is optimizing the supervisory AI policy to reduce heating demand while preserving the zero-comfort-violation behavior demonstrated in the seven-day PoC.

---

# 29. Technology Stack

| Component | Technology |
|---|---|
| Building Digital Twin | EnergyPlus 26.1 |
| AI Controller | Local Qwen LLM |
| Control Integration | EnergyPlus Python API |
| Core Controller | Python |
| Safety Logic | Deterministic Python Guards |
| Carbon Model | Python |
| Dashboard | Streamlit |
| Data Processing | Pandas |
| Live Communication | JSON State Files |
| Evaluation | Python / CSV |
| Building Model | EnergyPlus IDF |

---

# 30. Conclusion

This project demonstrates a complete proof-of-concept architecture for integrating generative AI with a building digital twin.

The system successfully implements:

- Live EnergyPlus state extraction
- Local Qwen LLM supervisory control
- Structured AI decisions
- Semantic validation
- Deterministic HVAC safety enforcement
- Real-time occupant comfort protection
- Carbon-aware decision context
- Fail-safe operation
- Automatic EnergyPlus actuator control
- AI-governance telemetry
- Operational data logging
- Baseline-vs-AI evaluation
- Live Streamlit visualization

The key contribution is not unrestricted LLM control, but a **hybrid AI + deterministic safety architecture** in which the LLM provides high-level reasoning while conventional software guarantees critical operational constraints.

The seven-day evaluation maintained a **0.00% occupied comfort-violation rate** for both baseline and AI control while demonstrating multiple successful semantic and safety interventions.

Energy and carbon results indicate that further optimization of the supervisory policy is required, providing a clear direction for future development.

---

## Honeywell Campus Connect Submission

**Project:** Autonomous AI-Powered Building Management System

**Core Technologies:** EnergyPlus 26.1, Python, Local Qwen LLM, Streamlit

**Control Architecture:** Closed-loop LLM supervisory control with deterministic semantic, safety and real-time comfort protection.
