import subprocess
from pathlib import Path


ENERGYPLUS_EXE = Path(
    r"C:\EnergyPlusV26-1-0\energyplus.exe"
)

MODEL_PATH = Path(
    r"building\models\5ZoneAI.idf"
)

WEATHER_PATH = Path(
    r"building\weather\chicago.epw"
)

OUTPUT_DIR = Path(
    r"results\python_baseline"
)


def run_energyplus():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    command = [
        str(ENERGYPLUS_EXE),
        "-r",
        "-w",
        str(WEATHER_PATH),
        "-d",
        str(OUTPUT_DIR),
        str(MODEL_PATH)
    ]

    print("Starting EnergyPlus simulation...")
    print("-" * 50)

    result = subprocess.run(
        command,
        text=True
    )

    print("-" * 50)

    if result.returncode == 0:
        print("EnergyPlus simulation completed successfully.")

        csv_file = OUTPUT_DIR / "eplusout.csv"

        if csv_file.exists():
            print(f"CSV generated: {csv_file}")
        else:
            print("Simulation succeeded, but CSV was not generated.")

    else:
        print("EnergyPlus simulation failed.")


if __name__ == "__main__":
    run_energyplus()