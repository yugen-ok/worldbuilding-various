
import traci
import time
import os
import csv
from pathlib import Path


# ---------- CONFIG ----------
SUMO_CFG = r"C:\Users\Yugen\sumo\manhattan\data\manhattan.sumocfg"
LOG_DIR = Path(r"C:\Users\Yugen\sumo\manhattan\logs")
MAX_FILES = 100
STEP_DELAY = 0.03
# ----------------------------

assert os.path.exists(SUMO_CFG)

LOG_DIR.mkdir(parents=True, exist_ok=True)

# Clean TraCI state (important for IPython)
if traci.isLoaded():
    traci.close()

traci.start([
    "sumo-gui",
    "-c", SUMO_CFG,
    "--start"
])

def rotate_logs():
    files = sorted(LOG_DIR.glob("step_*.csv"))
    while len(files) >= MAX_FILES:
        files[0].unlink()
        files.pop(0)

step_idx = 0

while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()
    sim_time = traci.simulation.getTime()

    # Rotate old files
    rotate_logs()

    # Write one CSV for this timestep
    csv_path = LOG_DIR / f"step_{step_idx:06d}.csv"

    with open(csv_path, "w", newline="", encoding="utf8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "time",
            "vehicle_id",
            "vehicle_type",
            "route_id",
            "x",
            "y",
            "speed",
            "accel",
            "lane_id",
            "edge_id"
        ])

        for vid in traci.vehicle.getIDList():
            x, y = traci.vehicle.getPosition(vid)
            writer.writerow([
                sim_time,
                vid,
                traci.vehicle.getTypeID(vid),
                traci.vehicle.getRouteID(vid),
                x,
                y,
                traci.vehicle.getSpeed(vid),
                traci.vehicle.getAcceleration(vid),
                traci.vehicle.getLaneID(vid),
                traci.vehicle.getRoadID(vid)
            ])

    step_idx += 1
    time.sleep(STEP_DELAY)

traci.close()
