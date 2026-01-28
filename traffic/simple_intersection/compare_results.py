#!/usr/bin/env python3
"""
Compare results from different configuration runs
"""

import json
from pathlib import Path
from datetime import datetime

def load_latest_logs():
    """Load the most recent log file for each config type"""
    logs_dir = Path("logs")

    if not logs_dir.exists():
        print("No logs directory found. Run simulations first.")
        return None, None

    # Find latest adaptive and naive logs
    adaptive_logs = sorted(logs_dir.glob("simulation_adaptive_config_*.json"))
    naive_logs = sorted(logs_dir.glob("simulation_naive_config_*.json"))

    adaptive = adaptive_logs[-1] if adaptive_logs else None
    naive = naive_logs[-1] if naive_logs else None

    return adaptive, naive


def analyze_log(log_file):
    """Extract key metrics from a log file"""
    with open(log_file) as f:
        data = json.load(f)

    config_name = data["metadata"]["config_name"]
    final_state = data["states"][-1]
    metrics = final_state["metrics"]

    return {
        "config_name": config_name,
        "file": log_file.name,
        "timestamp": data["metadata"]["start_time"],
        "avg_waiting_time": metrics["avg_waiting_time"],
        "avg_queue_length": metrics["avg_queue_length"],
        "avg_speed": metrics["avg_speed"],
        "objective_value": metrics["objective_value"],
        "vehicles_passed": metrics["vehicles_passed"]
    }


def compare_configs(adaptive_log, naive_log):
    """Compare two configuration results"""

    print("="*70)
    print("CONFIGURATION COMPARISON")
    print("="*70)

    if not adaptive_log or not naive_log:
        print("\nMissing log files!")
        if not adaptive_log:
            print("  - No adaptive_config logs found")
        if not naive_log:
            print("  - No naive_config logs found")
        print("\nRun both simulations first:")
        print("  python traffic_controller_configurable.py configs/adaptive_config.json")
        print("  python traffic_controller_configurable.py configs/naive_config.json")
        return

    adaptive_results = analyze_log(adaptive_log)
    naive_results = analyze_log(naive_log)

    print(f"\nAdaptive Config: {adaptive_results['file']}")
    print(f"  Timestamp: {adaptive_results['timestamp']}")
    print(f"  Average waiting time: {adaptive_results['avg_waiting_time']:.2f}s")
    print(f"  Average queue length: {adaptive_results['avg_queue_length']:.2f} vehicles")
    print(f"  Average speed: {adaptive_results['avg_speed']:.2f} m/s")
    print(f"  Objective value: {adaptive_results['objective_value']:.2f}")

    print(f"\nNaive Config: {naive_results['file']}")
    print(f"  Timestamp: {naive_results['timestamp']}")
    print(f"  Average waiting time: {naive_results['avg_waiting_time']:.2f}s")
    print(f"  Average queue length: {naive_results['avg_queue_length']:.2f} vehicles")
    print(f"  Average speed: {naive_results['avg_speed']:.2f} m/s")
    print(f"  Objective value: {naive_results['objective_value']:.2f}")

    print("\n" + "="*70)
    print("PERFORMANCE DIFFERENCE (Naive vs Adaptive)")
    print("="*70)

    wait_diff = naive_results['avg_waiting_time'] - adaptive_results['avg_waiting_time']
    wait_pct = (wait_diff / adaptive_results['avg_waiting_time']) * 100 if adaptive_results['avg_waiting_time'] > 0 else 0

    queue_diff = naive_results['avg_queue_length'] - adaptive_results['avg_queue_length']
    queue_pct = (queue_diff / adaptive_results['avg_queue_length']) * 100 if adaptive_results['avg_queue_length'] > 0 else 0

    obj_diff = naive_results['objective_value'] - adaptive_results['objective_value']
    obj_pct = (obj_diff / adaptive_results['objective_value']) * 100 if adaptive_results['objective_value'] > 0 else 0

    print(f"\nWaiting Time:")
    print(f"  Difference: {wait_diff:+.2f}s ({wait_pct:+.1f}%)")
    print(f"  Status: {'✓ Naive is WORSE (as expected)' if wait_diff > 0 else '✗ Unexpected result'}")

    print(f"\nQueue Length:")
    print(f"  Difference: {queue_diff:+.2f} vehicles ({queue_pct:+.1f}%)")
    print(f"  Status: {'✓ Naive is WORSE (as expected)' if queue_diff > 0 else '✗ Unexpected result'}")

    print(f"\nObjective Value:")
    print(f"  Difference: {obj_diff:+.2f} ({obj_pct:+.1f}%)")
    print(f"  Status: {'✓ Naive is WORSE (as expected)' if obj_diff > 0 else '✗ Unexpected result'}")

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)

    if obj_diff > 0:
        improvement = (obj_diff / naive_results['objective_value']) * 100
        print(f"\n✓ Adaptive control performs BETTER than naive control")
        print(f"  Adaptive reduces objective by {improvement:.1f}% compared to naive")
        print(f"  This confirms the adaptive controller is working as intended!")
    else:
        print(f"\n✗ Unexpected: Naive control performed better or equal")
        print(f"  This may indicate:")
        print(f"    - Traffic patterns where fixed timing works well")
        print(f"    - Need to adjust adaptive parameters")
        print(f"    - Random variation (run multiple times)")

    print()


if __name__ == "__main__":
    adaptive_log, naive_log = load_latest_logs()
    compare_configs(adaptive_log, naive_log)
