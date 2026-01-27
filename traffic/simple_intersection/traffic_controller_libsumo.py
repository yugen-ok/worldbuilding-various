#!/usr/bin/env python3
"""
Traffic Light Controller using libsumo (no subprocess)
=======================================================

This version uses libsumo instead of traci, which avoids subprocess
creation and should bypass Windows Application Control restrictions.

libsumo loads SUMO as a library rather than spawning a new process.
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add SUMO tools to path
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please set SUMO_HOME environment variable")

# Use libsumo instead of traci - no subprocess needed!
try:
    import libsumo as traci
    print("Using libsumo (library mode - no subprocess)")
except ImportError:
    print("ERROR: libsumo not available, falling back to traci")
    print("To install libsumo: pip install eclipse-sumo")
    import traci

# Same configuration as before
class Config:
    SUMO_CFG = "simulation.sumocfg"
    SIMULATION_STEPS = 600
    LOG_DIR = Path("logs")
    LOG_INTERVAL = 10
    MIN_GREEN_TIME = 10
    MAX_GREEN_TIME = 60
    YELLOW_TIME = 3
    QUEUE_THRESHOLD = 5


class TrafficMetrics:
    """Calculate and track traffic performance metrics"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.vehicle_waiting_times = []
        self.vehicle_speeds = []
        self.vehicles_passed = 0
        self.total_queue_length = 0
        self.measurements = 0

    def update(self, waiting_times, speeds, queue_length):
        self.vehicle_waiting_times.extend(waiting_times)
        self.vehicle_speeds.extend(speeds)
        self.total_queue_length += queue_length
        self.measurements += 1

    def calculate(self):
        avg_waiting_time = (
            sum(self.vehicle_waiting_times) / len(self.vehicle_waiting_times)
            if self.vehicle_waiting_times else 0.0
        )
        avg_speed = (
            sum(self.vehicle_speeds) / len(self.vehicle_speeds)
            if self.vehicle_speeds else 0.0
        )
        avg_queue_length = (
            self.total_queue_length / self.measurements
            if self.measurements > 0 else 0.0
        )

        objective_value = avg_waiting_time + (avg_queue_length * 2)

        return {
            "avg_waiting_time": avg_waiting_time,
            "avg_speed": avg_speed,
            "avg_queue_length": avg_queue_length,
            "vehicles_passed": self.vehicles_passed,
            "objective_value": objective_value
        }


class SimulationLogger:
    """Log simulation state and metrics"""

    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"simulation_libsumo_{timestamp}.json"

        self.log_data = {
            "metadata": {
                "start_time": datetime.now().isoformat(),
                "mode": "libsumo",
                "configuration": {
                    "min_green_time": Config.MIN_GREEN_TIME,
                    "max_green_time": Config.MAX_GREEN_TIME,
                    "simulation_duration": Config.SIMULATION_STEPS,
                },
                "objective": {
                    "description": "Minimize average waiting time and queue length",
                    "formula": "objective = avg_waiting_time + (avg_queue_length * 2)"
                }
            },
            "states": []
        }

    def log_state(self, sim_time, traffic_lights, vehicles, metrics):
        state = {
            "time": sim_time,
            "traffic_lights": traffic_lights,
            "vehicle_count": len(vehicles),
            "vehicles": vehicles,
            "metrics": metrics
        }
        self.log_data["states"].append(state)

    def save(self):
        self.log_data["metadata"]["end_time"] = datetime.now().isoformat()

        with open(self.log_file, 'w') as f:
            json.dump(self.log_data, f, indent=2)

        print(f"\nLog saved to: {self.log_file}")
        return self.log_file


class AdaptiveTrafficController:
    """Adaptive traffic light controller"""

    def __init__(self, tl_id):
        self.tl_id = tl_id
        self.current_phase_duration = 0
        self.phase_start_time = 0
        self.controlled_lanes = traci.trafficlight.getControlledLanes(tl_id)
        self.controlled_links = traci.trafficlight.getControlledLinks(tl_id)

        print(f"\nController initialized for traffic light: {tl_id}")
        print(f"  Controlled lanes: {len(set(self.controlled_lanes))}")

    def get_approach_queues(self):
        queues = {}
        for lane in set(self.controlled_lanes):
            if lane:
                queue_length = traci.lane.getLastStepHaltingNumber(lane)
                edge = traci.lane.getEdgeID(lane)
                if edge not in queues:
                    queues[edge] = 0
                queues[edge] += queue_length
        return queues

    def get_approach_waiting_times(self):
        waiting_times = {}
        for lane in set(self.controlled_lanes):
            if lane:
                vehicles = traci.lane.getLastStepVehicleIDs(lane)
                edge = traci.lane.getEdgeID(lane)
                if vehicles:
                    avg_wait = sum(traci.vehicle.getWaitingTime(v) for v in vehicles) / len(vehicles)
                    waiting_times[edge] = avg_wait
                else:
                    waiting_times[edge] = 0.0
        return waiting_times

    def should_switch_phase(self, sim_time):
        phase_duration = sim_time - self.phase_start_time

        if phase_duration < Config.MIN_GREEN_TIME:
            return False

        if phase_duration >= Config.MAX_GREEN_TIME:
            return True

        queues = self.get_approach_queues()
        waiting_times = self.get_approach_waiting_times()
        current_phase = traci.trafficlight.getPhase(self.tl_id)
        current_state = traci.trafficlight.getRedYellowGreenState(self.tl_id)

        current_green_lanes = [
            lane for i, lane in enumerate(self.controlled_lanes)
            if lane and i < len(current_state) and current_state[i] in ['G', 'g']
        ]

        if current_green_lanes:
            current_queue = sum(
                traci.lane.getLastStepHaltingNumber(lane)
                for lane in set(current_green_lanes)
            )
            total_queue = sum(queues.values())
            other_queue = total_queue - current_queue

            if other_queue > current_queue + Config.QUEUE_THRESHOLD:
                return True

        return False

    def control_step(self, sim_time):
        if self.should_switch_phase(sim_time):
            current_phase = traci.trafficlight.getPhase(self.tl_id)
            phase_count = len(traci.trafficlight.getAllProgramLogics(self.tl_id)[0].phases)
            next_phase = (current_phase + 1) % phase_count

            traci.trafficlight.setPhase(self.tl_id, next_phase)
            self.phase_start_time = sim_time
            return True
        return False


def collect_vehicle_data():
    vehicles = []
    for veh_id in traci.vehicle.getIDList():
        vehicles.append({
            "id": veh_id,
            "position": traci.vehicle.getPosition(veh_id),
            "speed": traci.vehicle.getSpeed(veh_id),
            "waiting_time": traci.vehicle.getWaitingTime(veh_id),
            "lane": traci.vehicle.getLaneID(veh_id),
            "edge": traci.vehicle.getRoadID(veh_id)
        })
    return vehicles


def collect_traffic_light_data(tl_ids):
    tl_data = {}
    for tl_id in tl_ids:
        tl_data[tl_id] = {
            "phase": traci.trafficlight.getPhase(tl_id),
            "state": traci.trafficlight.getRedYellowGreenState(tl_id),
            "phase_duration": traci.trafficlight.getPhaseDuration(tl_id),
            "next_switch": traci.trafficlight.getNextSwitch(tl_id)
        }
    return tl_data


def run_simulation():
    """Main simulation loop with adaptive traffic control"""

    print("="*60)
    print("ADAPTIVE TRAFFIC CONTROLLER (libsumo mode)")
    print("="*60)
    print(f"\nObjective: Minimize waiting time and queue length")
    print(f"Formula: objective = avg_waiting_time + (avg_queue_length * 2)")
    print(f"\nSimulation duration: {Config.SIMULATION_STEPS} seconds")

    # Start SUMO with libsumo - no subprocess!
    sumo_args = [
        "-c", Config.SUMO_CFG,
        "--no-step-log", "true",
        "--no-warnings", "true"
    ]

    print(f"\nStarting SUMO (libsumo - library mode)...")

    # With libsumo, we use start() with command line args
    traci.start(sumo_args)

    # Initialize controller and logger
    tl_ids = traci.trafficlight.getIDList()
    if not tl_ids:
        print("ERROR: No traffic lights found in simulation!")
        traci.close()
        return

    controller = AdaptiveTrafficController(tl_ids[0])
    logger = SimulationLogger(Config.LOG_DIR)
    metrics = TrafficMetrics()

    print(f"\nRunning simulation...")
    last_log_time = 0
    phase_switches = 0

    # Main simulation loop
    for step in range(Config.SIMULATION_STEPS):
        traci.simulationStep()
        sim_time = traci.simulation.getTime()

        # Execute controller
        if controller.control_step(sim_time):
            phase_switches += 1

        # Collect metrics
        vehicles = collect_vehicle_data()
        waiting_times = [v["waiting_time"] for v in vehicles]
        speeds = [v["speed"] for v in vehicles]
        queues = controller.get_approach_queues()
        total_queue = sum(queues.values())

        metrics.update(waiting_times, speeds, total_queue)

        # Log at intervals
        if sim_time - last_log_time >= Config.LOG_INTERVAL:
            tl_data = collect_traffic_light_data(tl_ids)
            current_metrics = metrics.calculate()

            logger.log_state(sim_time, tl_data, vehicles, current_metrics)

            print(f"  t={sim_time:3.0f}s: "
                  f"vehicles={len(vehicles):3d}, "
                  f"queue={total_queue:3.0f}, "
                  f"avg_wait={current_metrics['avg_waiting_time']:5.1f}s, "
                  f"objective={current_metrics['objective_value']:6.1f}")

            last_log_time = sim_time

    # Final metrics
    final_metrics = metrics.calculate()

    print("\n" + "="*60)
    print("SIMULATION COMPLETE")
    print("="*60)
    print(f"\nFinal Metrics:")
    print(f"  Average waiting time: {final_metrics['avg_waiting_time']:.2f} seconds")
    print(f"  Average speed: {final_metrics['avg_speed']:.2f} m/s")
    print(f"  Average queue length: {final_metrics['avg_queue_length']:.2f} vehicles")
    print(f"  Total vehicles passed: {final_metrics['vehicles_passed']}")
    print(f"  Phase switches: {phase_switches}")
    print(f"  Objective value: {final_metrics['objective_value']:.2f} (lower is better)")

    log_file = logger.save()

    traci.close()

    return final_metrics, log_file


if __name__ == "__main__":
    try:
        metrics, log_file = run_simulation()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        if hasattr(traci, 'isLoaded') and traci.isLoaded():
            traci.close()
        sys.exit(1)
