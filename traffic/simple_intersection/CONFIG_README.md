# Configuration System - Quick Guide

## Overview

The traffic controller now uses **JSON configuration files** instead of hardcoded parameters. This allows easy experimentation with different control strategies.

## Quick Start

### Option 1: Interactive Selection (Recommended)

**Right-click** `RUN_COMPARE_CONFIGS.bat` → **"Run as administrator"**

You'll see:
```
Available configurations:
  1. Adaptive (Optimized) - Default
  2. Naive (Fixed-time, poor parameters)
  3. Both (run comparison)

Select configuration [1-3, default=1]:
```

- Press `1` (or wait 5 seconds) for adaptive control
- Press `2` for naive control
- Press `3` to run both and compare

### Option 2: Manual Execution

```cmd
# Adaptive (good) config
python traffic_controller_configurable.py configs/adaptive_config.json

# Naive (poor) config
python traffic_controller_configurable.py configs/naive_config.json

# Default (adaptive) if no config specified
python traffic_controller_configurable.py
```

### Option 3: Test Both Automatically

**Right-click** `TEST_CONFIGS.bat` → **"Run as administrator"**

Runs both configs sequentially and shows comparison.

---

## Configuration Files

### `configs/adaptive_config.json` (Optimized)

**Characteristics:**
- Min green: 10s (quick response)
- Max green: 60s (moderate)
- Queue threshold: 5 vehicles (sensitive)
- **Result:** Fast adaptation to traffic changes

**Parameters:**
```json
{
  "controller": {
    "min_green_time_seconds": 10,
    "max_green_time_seconds": 60,
    "queue_threshold_vehicles": 5,
    "waiting_time_threshold_seconds": 30
  }
}
```

### `configs/naive_config.json` (Poor Performance)

**Characteristics:**
- Min green: 45s (very slow response)
- Max green: 90s (excessive)
- Queue threshold: 20 vehicles (insensitive)
- **Result:** Behaves like bad fixed-time control

**Parameters:**
```json
{
  "controller": {
    "min_green_time_seconds": 45,
    "max_green_time_seconds": 90,
    "queue_threshold_vehicles": 20,
    "waiting_time_threshold_seconds": 120
  }
}
```

**Why naive underperforms:**
1. Long min green (45s) means slow reaction
2. High queue threshold (20) allows huge queues
3. High waiting threshold (120s) tolerates excessive delays
4. Acts like poorly-timed fixed control

---

## Expected Results

### Adaptive Config (Good)
```
Average waiting time: ~12-15 seconds
Average queue length: ~4-6 vehicles
Objective value: ~20-25 (LOWER is better)
```

### Naive Config (Poor)
```
Average waiting time: ~25-40 seconds
Average queue length: ~10-15 vehicles
Objective value: ~45-70 (HIGHER = worse)
```

**Naive should have 50-100% worse objective value than adaptive.**

---

## Comparing Results

### Method 1: Visual Comparison

Run both configs and compare the console output:
```
Objective value: 22.34 (adaptive)
Objective value: 56.78 (naive)
```

### Method 2: Automated Comparison

```cmd
python compare_results.py
```

This analyzes the log files and shows:
- Side-by-side metrics
- Percentage differences
- Verification that naive underperforms

Output example:
```
PERFORMANCE DIFFERENCE (Naive vs Adaptive)
========================================

Waiting Time:
  Difference: +18.45s (+127.2%)
  Status: ✓ Naive is WORSE (as expected)

Queue Length:
  Difference: +8.23 vehicles (+156.4%)
  Status: ✓ Naive is WORSE (as expected)

Objective Value:
  Difference: +34.91 (+152.3%)
  Status: ✓ Naive is WORSE (as expected)

CONCLUSION: Adaptive control performs BETTER
```

---

## Configuration Format

### Complete JSON Structure

```json
{
  "name": "Config Name",
  "description": "What makes this config special",

  "simulation": {
    "sumo_config": "simulation.sumocfg",
    "duration_seconds": 600,
    "use_gui": false
  },

  "logging": {
    "log_directory": "logs",
    "log_interval_seconds": 10,
    "save_vehicle_details": true
  },

  "controller": {
    "min_green_time_seconds": 10,
    "max_green_time_seconds": 60,
    "yellow_time_seconds": 3,
    "queue_threshold_vehicles": 5,
    "waiting_time_threshold_seconds": 30
  },

  "objective": {
    "description": "What we're optimizing",
    "formula": "avg_waiting_time + (avg_queue_length * 2)",
    "queue_weight": 2.0
  }
}
```

### Key Parameters Explained

**min_green_time_seconds**
- How long green stays on minimum
- Lower = more responsive
- Too low = excessive switching

**max_green_time_seconds**
- Maximum duration before forced switch
- Ensures fairness
- Too high = some approaches starve

**queue_threshold_vehicles**
- Queue difference needed to trigger switch
- Lower = more sensitive to queues
- Too low = unstable switching

**queue_weight**
- How much to weigh queue vs waiting time in objective
- Default 2.0 = queues matter twice as much

---

## Creating Custom Configs

1. **Copy existing config:**
   ```cmd
   copy configs\adaptive_config.json configs\my_config.json
   ```

2. **Edit parameters** in your favorite editor

3. **Run with your config:**
   ```cmd
   python traffic_controller_configurable.py configs/my_config.json
   ```

4. **Compare results:**
   ```cmd
   python compare_results.py
   ```

---

## Experiment Ideas

### Very Aggressive Control
```json
{
  "min_green_time_seconds": 5,
  "max_green_time_seconds": 30,
  "queue_threshold_vehicles": 2
}
```
Hypothesis: Might be too twitchy, excessive switching

### Conservative Control
```json
{
  "min_green_time_seconds": 20,
  "max_green_time_seconds": 45,
  "queue_threshold_vehicles": 10
}
```
Hypothesis: More stable but slower to react

### Queue-Focused
```json
{
  "queue_threshold_vehicles": 3,
  "queue_weight": 5.0
}
```
Hypothesis: Prioritizes clearing queues over waiting time

---

## Log Files

Logs are saved as: `logs/simulation_{config_name}_{timestamp}.json`

Examples:
- `simulation_adaptive_config_20260128_120000.json`
- `simulation_naive_config_20260128_120530.json`

Each log contains:
- Full configuration used
- State snapshots every 10 seconds
- Vehicle data (positions, speeds, waiting times)
- Traffic light states
- Calculated metrics

---

## Troubleshooting

**"Config file not found"**
→ Make sure you're running from the `simple_intersection` directory
→ Config paths are relative

**"No logs to compare"**
→ Run simulations first to generate logs
→ Both configs need to have been run at least once

**Results don't make sense**
→ Traffic has random variation - run multiple times
→ Check that SUMO simulation completed fully
→ Verify configs are actually different

---

## Summary

✅ **Configs are now JSON files** (easy to edit)
✅ **Two configs provided** (adaptive vs naive)
✅ **Naive underperforms** (as designed)
✅ **Easy comparison** (automated scripts)
✅ **Interactive selection** (batch file menu)

**To run:** Right-click `RUN_COMPARE_CONFIGS.bat` → "Run as administrator" → Select option
