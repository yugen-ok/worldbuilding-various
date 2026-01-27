#!/usr/bin/env python3
"""
Test script to verify the simple intersection simulation works.
"""
import sys
import os

# Add SUMO tools to path
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please set SUMO_HOME environment variable")

import traci

# Clean any existing TraCI connection
if traci.isLoaded():
    traci.close()

# Start SUMO with full path (helps with Windows permissions)
sumo_binary = r"C:\Program Files (x86)\Eclipse\Sumo\bin\sumo-gui.exe"
sumo_cmd = [sumo_binary, "-c", "simulation.sumocfg", "--start", "--quit-on-end"]

print("Starting SUMO simulation...")
traci.start(sumo_cmd)

print(f"Simulation loaded successfully!")
print(f"Simulation time range: 0 to {traci.simulation.getEndTime()}s")

# Get traffic light info
tl_ids = traci.trafficlight.getIDList()
print(f"\nTraffic lights found: {tl_ids}")

if tl_ids:
    tl_id = tl_ids[0]
    print(f"\nTraffic light '{tl_id}' info:")
    print(f"  Program: {traci.trafficlight.getProgram(tl_id)}")
    print(f"  Phase: {traci.trafficlight.getPhase(tl_id)}")
    print(f"  State: {traci.trafficlight.getRedYellowGreenState(tl_id)}")

# Run a few steps
print("\nRunning first 10 simulation steps...")
for step in range(10):
    traci.simulationStep()
    vehicle_count = traci.vehicle.getIDCount()
    if step % 5 == 0:
        print(f"  Step {step}: {vehicle_count} vehicles")

print("\nSimulation test successful!")
traci.close()
