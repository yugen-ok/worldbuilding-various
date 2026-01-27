# Adaptive Traffic Light Controller

A simple traffic optimization system that adjusts traffic light timing to minimize vehicle waiting times and queue lengths.

## Overview

This simulation demonstrates adaptive traffic light control using SUMO (Simulation of Urban MObility). The controller monitors real-time traffic conditions and adjusts signal timing to optimize flow.

### Objective Function

**Minimize:** `avg_waiting_time + (avg_queue_length × 2)`

This objective balances two goals:
1. Reduce how long vehicles wait at red lights
2. Prevent long queues from forming at intersections

Lower values indicate better performance.

## Files

### Simulation Files
- `network.nod.xml` - Junction/node definitions (5 nodes: center + 4 endpoints)
- `network.edg.xml` - Road/edge definitions (8 edges, 2 lanes each)
- `network.net.xml` - Generated network file (created by netconvert)
- `routes.rou.xml` - Vehicle flows (1400 vehicles/hour total, various routes)
- `simulation.sumocfg` - SUMO configuration (10-minute simulation)

### Control & Logging
- `traffic_controller.py` - Main adaptive controller with comprehensive logging
- `test_simulation.py` - Simple test to verify setup works
- `logs/` - Output directory for simulation logs (JSON format)

## Network Layout

```
        North
          |
          |
West -----+-----  East
          |
          |
        South
```

- **4-way intersection** with traffic light at center
- **2 lanes per approach** (allows for turning movements)
- **Traffic flows:**
  - North/South: 400 veh/h each (higher traffic)
  - East/West: 300 veh/h each
  - Mix of straight, left turn, and right turn movements

## Controller Logic

### Adaptive Strategy

The controller adjusts green phase duration based on:

1. **Queue lengths** - Extends green for approaches with longer queues
2. **Waiting times** - Switches if vehicles have been waiting too long
3. **Time constraints:**
   - Minimum green: 10 seconds (prevent rapid switching)
   - Maximum green: 60 seconds (ensure fairness)
   - Yellow time: 3 seconds (safety transition)

### Decision Rule

Switch to next phase if:
- Current phase has run for minimum duration (10s) AND
  - Maximum time reached (60s), OR
  - Current approach queue < 5 vehicles and opposing queue is much longer

This balances efficiency (clear queues quickly) with fairness (don't starve any approach).

## Logging

Each simulation generates a detailed JSON log containing:

### Metadata
- Configuration parameters
- Objective function definition
- Simulation start/end times

### State Data (logged every 10 seconds)
- **Time:** Simulation time
- **Traffic lights:** Phase, state, duration, next switch time
- **Vehicles:** Count, position, speed, waiting time, lane, edge
- **Metrics:**
  - Average waiting time (seconds)
  - Average speed (m/s)
  - Average queue length (vehicles)
  - Vehicles passed through
  - Objective value (optimization target)

### Log Format

```json
{
  "metadata": {
    "start_time": "2026-01-27T23:30:00",
    "configuration": {...},
    "objective": {
      "description": "Minimize average waiting time and queue length",
      "formula": "objective = avg_waiting_time + (avg_queue_length * 2)"
    }
  },
  "states": [
    {
      "time": 0,
      "traffic_lights": {...},
      "vehicle_count": 12,
      "vehicles": [...],
      "metrics": {
        "avg_waiting_time": 5.2,
        "avg_speed": 8.3,
        "avg_queue_length": 3.5,
        "objective_value": 12.2
      }
    },
    ...
  ]
}
```

## Usage

### Prerequisites

1. **SUMO installation** (Simulation of Urban MObility)
   - Download from: https://sumo.dlr.de/
   - Set `SUMO_HOME` environment variable

2. **Python packages**
   ```bash
   pip install traci  # SUMO's Traffic Control Interface
   ```

### Running the Simulation

```bash
# Set SUMO_HOME (adjust path for your installation)
export SUMO_HOME="/c/Program Files (x86)/Eclipse/Sumo"  # Windows Git Bash
# or
export SUMO_HOME="/usr/share/sumo"  # Linux

# Run the adaptive controller (headless)
python traffic_controller.py

# Or with GUI for visualization
# Edit traffic_controller.py and set: Config.USE_GUI = True
```

### Configuration

Edit `traffic_controller.py` to adjust parameters:

```python
class Config:
    SIMULATION_STEPS = 600  # Duration (seconds)
    USE_GUI = False  # Set True for visual debugging

    MIN_GREEN_TIME = 10  # Minimum phase duration
    MAX_GREEN_TIME = 60  # Maximum phase duration
    YELLOW_TIME = 3  # Yellow phase duration

    LOG_INTERVAL = 10  # Logging frequency
    QUEUE_THRESHOLD = 5  # Queue difference for switching
```

## Output

Console output shows real-time progress:
```
====================================================
ADAPTIVE TRAFFIC LIGHT CONTROLLER
====================================================

Objective: Minimize waiting time and queue length
Formula: objective = avg_waiting_time + (avg_queue_length * 2)

Simulation duration: 600 seconds
Min green time: 10s
Max green time: 60s

Running simulation...
  t=  0s: vehicles=  3, queue=  2, avg_wait=  0.5s, objective=   4.5
  t= 10s: vehicles= 15, queue=  5, avg_wait=  3.2s, objective=  13.2
  t= 20s: vehicles= 28, queue=  8, avg_wait=  5.7s, objective=  21.7
  ...

====================================================
SIMULATION COMPLETE
====================================================

Final Metrics:
  Average waiting time: 12.34 seconds
  Average speed: 7.82 m/s
  Average queue length: 4.56 vehicles
  Total vehicles passed: 187
  Phase switches: 24
  Objective value: 21.46 (lower is better)

Log saved to: logs/simulation_20260127_233000.json
```

## Comparison with Fixed-Time Control

To compare performance:
1. Run with adaptive controller (current implementation)
2. Disable adaptive logic (set fixed phase durations)
3. Compare objective values - adaptive should be lower

## Extensions

Possible improvements:
- **Machine learning**: Learn optimal timings from historical data
- **Predictive control**: Anticipate future traffic based on patterns
- **Multi-intersection**: Coordinate multiple traffic lights
- **Priority vehicles**: Give green waves to emergency vehicles
- **Pedestrian phases**: Include crosswalk signals

## Troubleshooting

**"SUMO_HOME not set"**
- Set the environment variable to your SUMO installation directory

**"Application Control policy blocked this file"**
- Windows security may block SUMO executable
- Try running from installation directory or adjust security settings
- Use full path to executable in script

**"No traffic lights found"**
- Verify `network.net.xml` was generated correctly
- Check that center node has `type="traffic_light"`

## References

- SUMO Documentation: https://sumo.dlr.de/docs/
- TraCI API: https://sumo.dlr.de/docs/TraCI.html
- Traffic light control: https://sumo.dlr.de/docs/Simulation/Traffic_Lights.html
