#!/usr/bin/env python3
"""
Traffic Light Controller with Optimization
==========================================

A simple adaptive traffic light controller that optimizes traffic flow
by adjusting signal timing based on real-time traffic conditions.

Objective Function:
- Minimize average vehicle waiting time at the intersection
- Maximize throughput (vehicles passing through per unit time)
- Minimize queue lengths at traffic lights

The controller uses a simple rule-based approach:
- Monitor queue lengths and waiting times for each approach
- Extend green phase for approaches with longer queues
- Switch to the next phase when current phase queue is cleared or max time reached
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

import traci

# =======================
# CONFIGURATION
# =======================

class Config:
    """Simulation and controller configuration"""
    # Simulation settings
    SUMO_CFG = "simulation.sumocfg"
    SIMULATION_STEPS = 600  # 10 minutes (600 seconds)
    USE_GUI = False  # Set to True for visual debugging

    # Logging settings
    LOG_DIR = Path("logs")
    LOG_INTERVAL = 10  # Log every N seconds

    # Controller settings
    MIN_GREEN_TIME = 10  # Minimum green phase duration (seconds)
    MAX_GREEN_TIME = 60  # Maximum green phase duration (seconds)
    YELLOW_TIME = 3  # Yellow phase duration (seconds)

    # Optimization thresholds
    QUEUE_THRESHOLD = 5  # Switch if opposing queue is this much longer
    WAITING_TIME_THRESHOLD = 30  # Maximum acceptable waiting time (seconds)


# =======================
# METRICS & LOGGING
# =======================

class TrafficMetrics:
    """Calculate and track traffic performance metrics"""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all metrics for new measurement period"""
        self.vehicle_waiting_times = []
        self.vehicle_speeds = []
        self.vehicles_passed = 0
        self.total_queue_length = 0
        self.measurements = 0

    def update(self, waiting_times, speeds, queue_length):
        """Update metrics with current measurements"""
        self.vehicle_waiting_times.extend(waiting_times)
        self.vehicle_speeds.extend(speeds)
        self.total_queue_length += queue_length
        self.measurements += 1

    def calculate(self):
        """Calculate aggregate metrics"""
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

        # Objective function: minimize waiting time and queue length
        # Lower is better
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
        self.log_file = self.log_dir / f"simulation_{timestamp}.json"

        self.log_data = {
            "metadata": {
                "start_time": datetime.now().isoformat(),
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
        """Log current simulation state"""
        state = {
            "time": sim_time,
            "traffic_lights": traffic_lights,
            "vehicle_count": len(vehicles),
            "vehicles": vehicles,
            "metrics": metrics
        }
        self.log_data["states"].append(state)

    def save(self):
        """Save log data to file"""
        self.log_data["metadata"]["end_time"] = datetime.now().isoformat()

        with open(self.log_file, 'w') as f:
            json.dump(self.log_data, f, indent=2)

        print(f"\nLog saved to: {self.log_file}")
        return self.log_file


# =======================
# TRAFFIC CONTROLLER
# =======================

class AdaptiveTrafficController:
    """
    Adaptive traffic light controller that adjusts timing based on traffic conditions.

    Strategy:
    - Monitor queue lengths at each approach to the intersection
    - Extend green time for approaches with longer queues
    - Switch when current approach is cleared or max time reached
    """

    def __init__(self, tl_id):
        self.tl_id = tl_id
        self.current_phase_duration = 0
        self.phase_start_time = 0

        # Get controlled lanes
        self.controlled_lanes = traci.trafficlight.getControlledLanes(tl_id)
        self.controlled_links = traci.trafficlight.getControlledLinks(tl_id)

        print(f"\nController initialized for traffic light: {tl_id}")
        print(f"  Controlled lanes: {len(set(self.controlled_lanes))}")

    def get_approach_queues(self):
        """Get queue length for each approach to the intersection"""
        queues = {}

        # Group lanes by approach direction
        for lane in set(self.controlled_lanes):
            if lane:  # Skip empty lane IDs
                queue_length = traci.lane.getLastStepHaltingNumber(lane)
                edge = traci.lane.getEdgeID(lane)

                if edge not in queues:
                    queues[edge] = 0
                queues[edge] += queue_length

        return queues

    def get_approach_waiting_times(self):
        """Get average waiting time for vehicles on each approach"""
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
        """
        Decide if we should switch to the next traffic light phase.

        Returns:
            bool: True if should switch, False otherwise
        """
        phase_duration = sim_time - self.phase_start_time

        # Don't switch if minimum green time not reached
        if phase_duration < Config.MIN_GREEN_TIME:
            return False

        # Always switch if maximum green time reached
        if phase_duration >= Config.MAX_GREEN_TIME:
            return True

        # Get current traffic state
        queues = self.get_approach_queues()
        waiting_times = self.get_approach_waiting_times()

        # Get current phase
        current_phase = traci.trafficlight.getPhase(self.tl_id)
        current_state = traci.trafficlight.getRedYellowGreenState(self.tl_id)

        # Simple heuristic: switch if current green lanes have small queue
        # and other approaches have large queues
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

            # Switch if opposing queue is significantly larger
            if other_queue > current_queue + Config.QUEUE_THRESHOLD:
                return True

        return False

    def control_step(self, sim_time):
        """Execute one control step"""
        # Check if we should switch phase
        if self.should_switch_phase(sim_time):
            # Get current phase and advance to next
            current_phase = traci.trafficlight.getPhase(self.tl_id)
            phase_count = len(traci.trafficlight.getAllProgramLogics(self.tl_id)[0].phases)
            next_phase = (current_phase + 1) % phase_count

            traci.trafficlight.setPhase(self.tl_id, next_phase)
            self.phase_start_time = sim_time

            return True  # Phase switched

        return False  # No change


# =======================
# MAIN SIMULATION
# =======================

def collect_vehicle_data():
    """Collect data about all vehicles in simulation"""
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
    """Collect data about all traffic lights"""
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
    print("ADAPTIVE TRAFFIC LIGHT CONTROLLER")
    print("="*60)
    print(f"\nObjective: Minimize waiting time and queue length")
    print(f"Formula: objective = avg_waiting_time + (avg_queue_length * 2)")
    print(f"\nSimulation duration: {Config.SIMULATION_STEPS} seconds")
    print(f"Min green time: {Config.MIN_GREEN_TIME}s")
    print(f"Max green time: {Config.MAX_GREEN_TIME}s")

    # Start SUMO
    sumo_binary = "sumo" if not Config.USE_GUI else "sumo-gui"
    sumo_cmd = [sumo_binary, "-c", Config.SUMO_CFG]
    if Config.USE_GUI:
        sumo_cmd.extend(["--start", "--quit-on-end"])

    print(f"\nStarting SUMO ({'GUI' if Config.USE_GUI else 'headless'})...")

    # Clean any existing connection
    if traci.isLoaded():
        traci.close()

    traci.start(sumo_cmd)

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

            # Print progress
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

    # Save log
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
        if traci.isLoaded():
            traci.close()
        sys.exit(1)
