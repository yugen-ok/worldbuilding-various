#!/usr/bin/env python3
"""
Traffic Light Controller with JSON Configuration
================================================

A simple adaptive traffic light controller that loads parameters from JSON config files.

Usage:
    python controller.py [config_file.json]

If no config file specified, defaults to configs/adaptive_config.json
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

USE_GUI = True

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
    """Simulation and controller configuration loaded from JSON"""

    def __init__(self, config_path="configs/adaptive_config.json"):
        """Load configuration from JSON file"""
        self.config_path = Path(config_path)

        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(self.config_path) as f:
            config_data = json.load(f)

        # Store original config data
        self.config_data = config_data

        # Extract values with defaults
        sim = config_data.get("simulation", {})
        self.SUMO_CFG = sim.get("sumo_config", "configs/simulation.sumocfg")
        self.SIMULATION_STEPS = sim.get("duration_seconds", 600)
        self.USE_GUI = USE_GUI

        log = config_data.get("logging", {})
        self.LOG_DIR = Path(log.get("log_directory", "logs"))
        self.LOG_INTERVAL = log.get("log_interval_seconds", 10)
        self.SAVE_VEHICLE_DETAILS = log.get("save_vehicle_details", True)

        ctrl = config_data.get("controller", {})
        self.MIN_GREEN_TIME = ctrl.get("min_green_time_seconds", 10)
        self.MAX_GREEN_TIME = ctrl.get("max_green_time_seconds", 60)
        self.YELLOW_TIME = ctrl.get("yellow_time_seconds", 3)
        self.QUEUE_THRESHOLD = ctrl.get("queue_threshold_vehicles", 5)
        self.WAITING_TIME_THRESHOLD = ctrl.get("waiting_time_threshold_seconds", 30)

        obj = config_data.get("objective", {})
        self.QUEUE_WEIGHT = obj.get("queue_weight", 2.0)

        # Config name and description
        self.NAME = config_data.get("name", "Traffic Controller")
        self.DESCRIPTION = config_data.get("description", "")

    def print_summary(self):
        """Print configuration summary"""
        print(f"\n{'='*60}")
        print(f"CONFIG: {self.NAME}")
        print(f"{'='*60}")
        print(f"Description: {self.DESCRIPTION}")
        print(f"Config file: {self.config_path}")
        print(f"\nSimulation:")
        print(f"  Duration: {self.SIMULATION_STEPS}s")
        print(f"  GUI: {'Yes' if self.USE_GUI else 'No (headless)'}")
        print(f"\nController Parameters:")
        print(f"  Min green time: {self.MIN_GREEN_TIME}s")
        print(f"  Max green time: {self.MAX_GREEN_TIME}s")
        print(f"  Yellow time: {self.YELLOW_TIME}s")
        print(f"  Queue threshold: {self.QUEUE_THRESHOLD} vehicles")
        print(f"  Waiting time threshold: {self.WAITING_TIME_THRESHOLD}s")
        print(f"\nObjective:")
        print(f"  Formula: avg_waiting_time + (avg_queue_length × {self.QUEUE_WEIGHT})")
        print(f"{'='*60}\n")


# =======================
# METRICS & LOGGING
# =======================

class TrafficMetrics:
    """Calculate and track traffic performance metrics"""

    def __init__(self, config):
        self.config = config
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

        # Objective function with configurable queue weight
        objective_value = avg_waiting_time + (avg_queue_length * self.config.QUEUE_WEIGHT)

        return {
            "avg_waiting_time": avg_waiting_time,
            "avg_speed": avg_speed,
            "avg_queue_length": avg_queue_length,
            "vehicles_passed": self.vehicles_passed,
            "objective_value": objective_value
        }


class SimulationLogger:
    """Log simulation state and metrics"""

    def __init__(self, config):
        self.config = config
        self.log_dir = Path(config.LOG_DIR)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_name = Path(config.config_path).stem
        self.log_file = self.log_dir / f"simulation_{config_name}_{timestamp}.json"

        self.log_data = {
            "metadata": {
                "start_time": datetime.now().isoformat(),
                "config_file": str(config.config_path),
                "config_name": config.NAME,
                "configuration": config.config_data,
            },
            "states": []
        }

    def log_state(self, sim_time, traffic_lights, vehicles, metrics):
        """Log current simulation state"""
        state = {
            "time": sim_time,
            "traffic_lights": traffic_lights,
            "vehicle_count": len(vehicles),
            "metrics": metrics
        }

        if self.config.SAVE_VEHICLE_DETAILS:
            state["vehicles"] = vehicles

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
    """

    def __init__(self, tl_id, config):
        self.tl_id = tl_id
        self.config = config
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

        for lane in set(self.controlled_lanes):
            if lane:
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
        """
        phase_duration = sim_time - self.phase_start_time

        # Don't switch if minimum green time not reached
        if phase_duration < self.config.MIN_GREEN_TIME:
            return False

        # Always switch if maximum green time reached
        if phase_duration >= self.config.MAX_GREEN_TIME:
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

            # Switch if opposing queue is significantly larger (uses config threshold)
            if other_queue > current_queue + self.config.QUEUE_THRESHOLD:
                return True

        return False

    def control_step(self, sim_time):
        """Execute one control step"""
        if self.should_switch_phase(sim_time):
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


def run_simulation(config):
    """Main simulation loop with adaptive traffic control"""

    config.print_summary()

    # Start SUMO
    sumo_binary = "sumo" if not config.USE_GUI else "sumo-gui"
    sumo_cmd = [sumo_binary, "-c", config.SUMO_CFG]
    if config.USE_GUI:
        sumo_cmd.extend(["--start", "--quit-on-end"])

    print(f"Starting SUMO ({'GUI' if config.USE_GUI else 'headless'})...")

    # Clean any existing connection
    if traci.isLoaded():
        traci.close()

    traci.start(sumo_cmd)

    # Initialize controller and logger
    tl_ids = traci.trafficlight.getIDList()
    if not tl_ids:
        print("ERROR: No traffic lights found in simulation!")
        traci.close()
        return None

    controller = AdaptiveTrafficController(tl_ids[0], config)
    logger = SimulationLogger(config)
    metrics = TrafficMetrics(config)

    print(f"\nRunning simulation...")
    last_log_time = 0
    phase_switches = 0

    # Main simulation loop
    for step in range(config.SIMULATION_STEPS):
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
        if sim_time - last_log_time >= config.LOG_INTERVAL:
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
    print(f"\nConfig: {config.NAME}")
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

    return {
        "config_name": config.NAME,
        "metrics": final_metrics,
        "log_file": str(log_file)
    }


if __name__ == "__main__":
    # Get config file from command line or use default
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = "configs/adaptive_config.json"

    try:
        # Load configuration
        config = Config(config_file)

        # Run simulation
        result = run_simulation(config)

        if result:
            print(f"\n{'='*60}")
            print(f"SUCCESS!")
            print(f"{'='*60}")
            print(f"Config: {result['config_name']}")
            print(f"Objective: {result['metrics']['objective_value']:.2f}")
            print(f"Log: {result['log_file']}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        if traci.isLoaded():
            traci.close()
        sys.exit(1)
