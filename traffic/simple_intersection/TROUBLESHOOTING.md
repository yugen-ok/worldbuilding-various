# Troubleshooting Windows Application Control Error

## Problem

```
OSError: [WinError 4551] An Application Control policy has blocked this file
```

This occurs when Windows Application Control or AppLocker prevents Python from launching SUMO as a subprocess.

---

## Solution 1: Run as Administrator ⭐ EASIEST

### Option A: Batch File (Windows)

1. **Double-click** `RUN_AS_ADMIN.bat`
2. When prompted, click **"Yes"** to allow administrator access
3. Simulation will run automatically

### Option B: Command Line

```cmd
# Open Command Prompt as Administrator
# Right-click Start → "Terminal (Admin)" or "Command Prompt (Admin)"

cd C:\Users\Yugen\gdrive\workspace\worldbuilding-various\traffic\simple_intersection

set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo

C:\Users\Yugen\gdrive\workspace\.venv\Scripts\python.exe traffic_controller.py
```

### Option C: PowerShell

```powershell
# Open PowerShell as Administrator
# Right-click Start → "Terminal (Admin)"

cd C:\Users\Yugen\gdrive\workspace\worldbuilding-various\traffic\simple_intersection

$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"

& C:\Users\Yugen\gdrive\workspace\.venv\Scripts\python.exe traffic_controller.py
```

**Why this works:** Administrator privileges bypass Application Control restrictions.

---

## Solution 2: Whitelist SUMO in Windows Security

### For Windows 10/11 Professional/Enterprise:

1. **Open Group Policy Editor:**
   - Press `Win + R`
   - Type `gpedit.msc`
   - Click OK

2. **Navigate to AppLocker:**
   - Computer Configuration → Windows Settings → Security Settings → Application Control Policies → AppLocker

3. **Create Exception:**
   - Right-click "Executable Rules" → Create New Rule
   - Allow all users to run: `C:\Program Files (x86)\Eclipse\Sumo\bin\*`

4. **Apply and restart**

### For Windows Home Edition:

Windows Home doesn't have Group Policy Editor. Use Solution 1 or 3 instead.

---

## Solution 3: Run SUMO Manually with TraCI Connection

Instead of Python launching SUMO, you can launch SUMO first and connect to it:

### Step 1: Start SUMO with TraCI Server

Open Command Prompt and run:
```cmd
cd C:\Program Files (x86)\Eclipse\Sumo\bin

sumo-gui.exe ^
  -c "C:\Users\Yugen\gdrive\workspace\worldbuilding-various\traffic\simple_intersection\simulation.sumocfg" ^
  --remote-port 8813 ^
  --start
```

This starts SUMO and waits for TraCI connection on port 8813.

### Step 2: Connect from Python

Create a new file `traffic_controller_remote.py`:

```python
import traci

# Connect to running SUMO instance
traci.init(port=8813)

# Now run the controller logic
# (rest of the code remains the same)
```

**Why this works:** SUMO is launched manually (no subprocess), Python just connects to it.

---

## Solution 4: Use Different Python Interpreter

Sometimes the issue is with specific Python installations. Try:

### A. System Python
```cmd
# If you have Python installed system-wide
python traffic_controller.py
```

### B. Anaconda/Miniconda
```cmd
conda activate base
python traffic_controller.py
```

### C. Python from Microsoft Store
```cmd
# Python from Windows Store may have different permissions
python3 traffic_controller.py
```

---

## Solution 5: Modify Security Policy (IT/Admin Only)

If you have access to Windows Security settings:

### Option A: Windows Defender Application Control

1. Open **Windows Security**
2. Go to **App & browser control**
3. Click **Exploit protection settings**
4. Under **Program settings**, add exception for `python.exe` and `sumo.exe`

### Option B: Disable Application Control (Temporary)

⚠️ **Only do this if you understand the security implications:**

```powershell
# Run PowerShell as Administrator
Set-MpPreference -DisableRealtimeMonitoring $true
```

To re-enable:
```powershell
Set-MpPreference -DisableRealtimeMonitoring $false
```

---

## Solution 6: Alternative - Run in Linux Subsystem (WSL)

If you have Windows Subsystem for Linux:

```bash
# Install WSL if not already
wsl --install

# In WSL Ubuntu:
sudo apt update
sudo apt install sumo sumo-tools python3-pip

# Navigate to your files
cd /mnt/c/Users/Yugen/gdrive/workspace/worldbuilding-various/traffic/simple_intersection

# Run simulation
export SUMO_HOME=/usr/share/sumo
python3 traffic_controller.py
```

**Why this works:** Linux doesn't have Windows Application Control.

---

## Verification Tests

### Test 1: Check SUMO Installation
```cmd
cd C:\Program Files (x86)\Eclipse\Sumo\bin
sumo-gui.exe --version
```

Should show SUMO version without errors.

### Test 2: Check Python Subprocess
```python
import subprocess
subprocess.run(["C:\\Program Files (x86)\\Eclipse\\Sumo\\bin\\sumo.exe", "--version"])
```

If this fails with Error 4551, subprocess is blocked.

### Test 3: Run Simple Simulation
```cmd
cd C:\Users\Yugen\gdrive\workspace\worldbuilding-various\traffic\simple_intersection

# Try headless
C:\Program^ Files^ (x86)\Eclipse\Sumo\bin\sumo.exe -c simulation.sumocfg
```

If this works but Python can't launch it, it's definitely Application Control.

---

## Quick Diagnosis

| Symptom | Cause | Solution |
|---------|-------|----------|
| Error 4551 | Application Control blocking | Solution 1 (Admin) |
| Error 2 (File not found) | Wrong SUMO path | Check SUMO_HOME |
| Error 10061 (Connection refused) | SUMO not running | Start SUMO first (Solution 3) |
| Import error (traci) | SUMO tools not in path | Set SUMO_HOME correctly |

---

## Recommended Approach

**For quick testing:**
1. Use `RUN_AS_ADMIN.bat` (Solution 1A)

**For permanent fix:**
1. Contact IT to whitelist SUMO (Solution 2)
2. Or set up WSL (Solution 6) for development

**For one-time use:**
1. Run as administrator (Solution 1)

---

## Still Having Issues?

### Check Logs
Look for detailed error messages in:
- Windows Event Viewer (Application Logs)
- SUMO log files (if SUMO starts at all)

### Contact Support
If this is a corporate machine, contact your IT department and explain:
- You need to run SUMO (traffic simulation software)
- It's for research/development purposes
- Request to whitelist: `C:\Program Files (x86)\Eclipse\Sumo\bin\*.exe`

### Alternative: Cloud Environment
Consider running the simulation in:
- Google Colab (with SUMO installed)
- AWS/Azure VM
- Docker container

---

## Summary

**Fastest Solution:** Run `RUN_AS_ADMIN.bat` as administrator

**Best Solution:** Whitelist SUMO in Windows Security (if you have permissions)

**Alternative:** Use WSL or run SUMO manually with remote connection
