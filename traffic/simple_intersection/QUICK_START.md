# Quick Start Guide - Traffic Controller

## ⚠️ Windows Security Issue Detected

Your system has **Application Control Policy** blocking SUMO execution.

---

## ✅ SOLUTION: Run as Administrator

### Method 1: Double-Click Batch File (EASIEST)

1. **Right-click** on `RUN_AS_ADMIN.bat`
2. Select **"Run as administrator"**
3. Click **"Yes"** when Windows asks for permission
4. Simulation will run automatically
5. Check `logs/` folder for results

### Method 2: Command Prompt (Alternative)

1. Press `Win + X`
2. Select **"Terminal (Admin)"** or **"Command Prompt (Admin)"**
3. Run these commands:

```cmd
cd C:\Users\Yugen\gdrive\workspace\worldbuilding-various\traffic\simple_intersection

set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo

C:\Users\Yugen\gdrive\workspace\.venv\Scripts\python.exe traffic_controller.py
```

---

## 📊 What Happens When It Runs

You'll see output like this:

```
============================================================
ADAPTIVE TRAFFIC LIGHT CONTROLLER
============================================================

Objective: Minimize waiting time and queue length
Formula: objective = avg_waiting_time + (avg_queue_length * 2)

Simulation duration: 600 seconds
Min green time: 10s
Max green time: 60s

Starting SUMO (headless)...

Controller initialized for traffic light: center
  Controlled lanes: 8

Running simulation...
  t=  0s: vehicles=  3, queue=  2, avg_wait=  0.5s, objective=   4.5
  t= 10s: vehicles= 15, queue=  5, avg_wait=  3.2s, objective=  13.2
  t= 20s: vehicles= 28, queue=  8, avg_wait=  5.7s, objective=  21.7
  ...
  t=590s: vehicles= 45, queue=  6, avg_wait=  8.3s, objective=  20.3

============================================================
SIMULATION COMPLETE
============================================================

Final Metrics:
  Average waiting time: 12.34 seconds
  Average speed: 7.82 m/s
  Average queue length: 4.56 vehicles
  Total vehicles passed: 187
  Phase switches: 24
  Objective value: 21.46 (lower is better)

Log saved to: logs/simulation_20260128_120000.json
```

---

## 📁 Output Files

After running, check the `logs/` directory:

```
logs/
  simulation_20260128_120000.json  ← Your results!
```

This JSON file contains:
- Complete vehicle data
- Traffic light states
- Performance metrics
- Objective function values

---

## 🔍 View Results

### In Command Line:
```cmd
type logs\simulation_*.json | more
```

### In Python:
```python
import json

with open("logs/simulation_20260128_120000.json") as f:
    data = json.load(f)

# Print final metrics
final = data["states"][-1]["metrics"]
print(f"Objective value: {final['objective_value']}")
print(f"Avg waiting time: {final['avg_waiting_time']}s")
print(f"Avg queue length: {final['avg_queue_length']} vehicles")
```

### In Browser:
Just open the `.json` file in your browser - it's formatted for readability!

---

## ⚙️ Customize Settings

Edit `traffic_controller.py` to change:

```python
class Config:
    SIMULATION_STEPS = 600  # Duration: 600 seconds = 10 minutes
    USE_GUI = False         # Set True to see visualization

    MIN_GREEN_TIME = 10     # Minimum green phase
    MAX_GREEN_TIME = 60     # Maximum green phase

    LOG_INTERVAL = 10       # Log every N seconds
```

---

## 🐛 Troubleshooting

**"Not recognized as administrator"**
→ Make sure you right-clicked and selected "Run as administrator", not just double-clicked

**"SUMO_HOME not set"**
→ The batch file sets it automatically, but verify SUMO is at:
  `C:\Program Files (x86)\Eclipse\Sumo`

**"Python not found"**
→ Check that virtual environment exists at:
  `C:\Users\Yugen\gdrive\workspace\.venv`

**Still getting Error 4551?**
→ See `TROUBLESHOOTING.md` for advanced solutions

---

## 📚 Next Steps

1. **Run baseline test:** Execute simulation as-is
2. **Check results:** View objective value in logs
3. **Compare:** Modify controller and run again
4. **Analyze:** Plot metrics over time

For detailed documentation, see `README.md`

---

## 💡 Why This Works

Running as administrator gives Python permission to launch SUMO, bypassing the Application Control policy that normally blocks it.

This is safe because:
- SUMO is legitimate traffic simulation software
- Your code only reads/writes local files
- No system modifications are made
- All data stays in `logs/` directory

---

## ✨ You're Ready!

Just **right-click** `RUN_AS_ADMIN.bat` → **"Run as administrator"** and you're done! 🚦

The simulation will run for 10 minutes (simulated time) and save comprehensive logs to the `logs/` folder.
