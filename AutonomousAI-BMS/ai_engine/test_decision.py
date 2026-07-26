import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT)
    )


from ai_engine.decision_engine import get_ai_decision


STATE_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "live_building_state.json"
)


print(
    "\n========================================"
)

print(
    "       AUTONOMOUS AI-BMS TEST"
)

print(
    "========================================"
)


with open(
    STATE_FILE,
    "r"
) as file:

    building_state = json.load(
        file
    )


print("\nBUILDING STATE")
print("----------------------------------------")

print(
    json.dumps(
        building_state,
        indent=2
    )
)


print("\nSending building state to LLM...")


decision = get_ai_decision(
    building_state
)


print("\nAI DECISION")
print("----------------------------------------")


if decision:

    print(
        json.dumps(
            decision,
            indent=2
        )
    )

else:

    print(
        "AI decision failed."
    )


print(
    "\n========================================"
)