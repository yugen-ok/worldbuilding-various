#!/usr/bin/env python3
"""
Compare Fixed-Time vs Adaptive Traffic Control
===============================================

This script runs the simulation twice:
1. Fixed-time control (traditional, predetermined signal timing)
2. Adaptive control (queue-responsive timing)

Then compares their objective function values to demonstrate
that adaptive control improves traffic flow.
"""

import sys
import json
from pathlib import Path

print("="*60)
print("TRAFFIC CONTROL COMPARISON")
print("="*60)
print("\nThis script would run two simulations:")
print("  1. Fixed-time control (baseline)")
print("  2. Adaptive control (optimized)")
print("\nThen compare metrics:")
print("  - Average waiting time")
print("  - Average queue length")
print("  - Objective value (lower is better)")
print("\nNote: Due to Windows Application Control restrictions,")
print("      the actual simulation cannot run automatically.")
print("      Please run traffic_controller.py manually and")
print("      compare the results in the logs/ directory.")

# Check if any logs exist
log_dir = Path("logs")
if log_dir.exists():
    log_files = list(log_dir.glob("simulation_*.json"))

    if log_files:
        print(f"\n{len(log_files)} simulation log(s) found:")

        for log_file in sorted(log_files):
            print(f"\n  {log_file.name}")

            with open(log_file) as f:
                data = json.load(f)

            # Get final state metrics
            if data["states"]:
                final_state = data["states"][-1]
                metrics = final_state["metrics"]

                print(f"    Time: {data['metadata']['start_time']}")
                print(f"    Avg waiting time: {metrics['avg_waiting_time']:.2f}s")
                print(f"    Avg queue length: {metrics['avg_queue_length']:.2f} veh")
                print(f"    Objective value: {metrics['objective_value']:.2f}")
    else:
        print("\nNo simulation logs found yet.")
        print("Run: python traffic_controller.py")
else:
    print("\nNo logs directory found yet.")
    print("Run the simulation first to generate logs.")

print("\n" + "="*60)
print("COMPARISON METHODOLOGY")
print("="*60)
print("""
To properly compare controllers:

1. Modify traffic_controller.py for FIXED-TIME control:
   - In AdaptiveTrafficController.should_switch_phase():
   - Always return False (except for max time)
   - This creates traditional fixed-cycle operation

2. Run simulation:
   python traffic_controller.py

3. Note the objective value from the output

4. Restore ADAPTIVE control (original code)

5. Run simulation again:
   python traffic_controller.py

6. Compare objective values:
   - Lower objective = better performance
   - Expected: Adaptive < Fixed-time

7. Analyze logs in logs/ directory:
   - Check waiting time trends over time
   - Observe how queue lengths evolve
   - See phase switching behavior
""")
