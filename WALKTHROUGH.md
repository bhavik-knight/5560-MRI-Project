# MRI Digital Twin - Complete Walkthrough

## 🎯 What This Project Does

This is a **real-time simulation** of an MRI department that shows how patients flow through the system. You'll see animated agents (circles for patients, triangles/squares for staff) moving around a floor plan, with live statistics tracking efficiency.

## 📋 Prerequisites

Before you start, make sure you have:

1. **Python 3.12** installed
   ```bash
   python --version  # Should show 3.12.x
   ```

2. **uv package manager** (recommended)
   ```bash
   # Install uv if you don't have it
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

## 🚀 Step-by-Step Setup

### Step 1: Navigate to Project Directory

```bash
cd /path/to/mri-project
```

### Step 2: Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install simpy pandas pygame plotly streamlit
```

### Step 3: Verify Installation

```bash
# Test that all modules import correctly
uv run python -c "from src.core.engine import run_simulation; print('✓ Ready to run!')"
```

You should see:
```
pygame 2.6.1 (SDL 2.28.4, Python 3.12.3)
Hello from the pygame community. https://www.pygame.org/contribute.html
✓ Ready to run!
```

## 🎮 Running the Simulation

### Basic Run

```bash
uv run python main.py
```

**What happens:**
1. A PyGame window opens showing the MRI floor plan
2. Patients (circles) start appearing in Zone 1 (bottom)
3. Staff (triangles/squares) move around helping patients
4. Simulation runs for 120 minutes (sim time)
5. Window closes and reports are generated

### Custom Runs

**Quick Test (5 minutes, 2 patients):**
```bash
uv run python main.py --duration 5 --patients 2
```

**Standard Run (2 hours, 10 patients):**
```bash
uv run python main.py --duration 120 --patients 10
```

**Full Day (8 hours, 20 patients):**
```bash
uv run python main.py --duration 480 --patients 20
```

**Custom Output Location:**
```bash
uv run python main.py --output my_experiment_1
```

## 👀 What to Watch For

### In the PyGame Window

1. **Patient Journey** (watch a circle):
   - Starts **grey** in Zone 1 (bottom)
   - Orange triangle (porter) escorts it to a teal box (change room)
   - Turns **blue** while changing
   - Cyan square (backup tech) escorts it to orange box (prep room)
   - Turns **yellow** and moves to yellow box (gowned waiting)
   - Purple square (scan tech) escorts it to cyan box (magnet)
   - Turns **green** while scanning
   - Exits to the right

2. **The Critical Buffer**:
   - Watch the **yellow box** (Gowned Waiting)
   - Patients turn **yellow** here while waiting for the magnet
   - This is the "Pit Crew" staging area

3. **Staff Movement**:
   - **Orange triangle** (porter) shuttles between Zone 1 and change rooms
   - **Cyan squares** (backup techs) move between prep rooms and staging
   - **Purple squares** (scan techs) stay near the magnets

### In the Console

You'll see:
```
============================================================
MRI DIGITAL TWIN - Starting Simulation
============================================================
Duration: 120 minutes
Max Patients: 10
Time Scale: 1 sim minute = 0.5 real seconds
============================================================

Starting simulation loop...
Close the window to end early.

[Simulation runs...]

============================================================
Simulation Complete
============================================================
Simulated Time: 120.0 minutes
Patients Completed: 8
============================================================

SIMULATION SUMMARY
============================================================
Duration: 120 minutes
Throughput: 8 patients
Magnet Busy (Value-Added): 73.2%
Magnet Idle: 8.5%
Avg Gowned Wait: 2.3 min
============================================================
```

## 📊 Understanding the Results

### Generated Files (in `results/` folder)

After the simulation, you'll find:

1. **`mri_digital_twin_movements.csv`**
   - Every time a patient moves to a new zone
   - Columns: `patient_id`, `zone`, `timestamp`, `event_type`

2. **`mri_digital_twin_states.csv`**
   - Every state change (grey → blue → yellow → green)
   - Columns: `patient_id`, `old_state`, `new_state`, `timestamp`

3. **`mri_digital_twin_gowned_waiting.csv`**
   - When patients enter/exit the buffer
   - Columns: `patient_id`, `timestamp`, `action`

4. **`mri_digital_twin_summary.csv`**
   - Single row with all key metrics
   - Use this for comparing different scenarios

5. **`mri_digital_twin_report.txt`**
   - Human-readable summary
   - Explains the "Utilization Paradox"

### Key Metrics Explained

**Throughput**: Number of patients who completed their scan

**Magnet Busy % (Value-Added)**: 
- Time the magnet spent actually scanning
- This is the "good" utilization

**Magnet Occupied %**:
- Total time the magnet was in use
- In serial workflow, this includes prep time (inefficient)
- In parallel workflow, this equals busy time (efficient)

**Magnet Idle %**:
- Time the magnet was truly idle
- Lower is better (but not if occupied ≠ busy!)

**The Paradox**:
```
Serial Workflow:   Occupied = 92%, Busy = 22%  ❌ (looks good, is bad)
Parallel Workflow: Occupied = 75%, Busy = 73%  ✓ (looks worse, is better)
```

## 🔧 Troubleshooting

### "Module not found" errors

```bash
# Make sure you're in the project directory
pwd  # Should show .../mri-project

# Reinstall dependencies
uv sync
```

### PyGame window doesn't open

```bash
# Check if pygame installed correctly
uv run python -c "import pygame; print(pygame.ver)"

# Try reinstalling pygame
uv pip install --force-reinstall pygame
```

### "Font initialization failed"

This is normal on some systems. The simulation will run without text labels, but the colored rooms will still show.

### Simulation runs too fast/slow

Edit `src/config.py`:
```python
SIM_SPEED = 0.5  # Change this value
# 0.5 = 1 sim minute = 0.5 real seconds
# 1.0 = 1 sim minute = 1 real second (slower)
# 0.25 = 1 sim minute = 0.25 real seconds (faster)
```

## 🎓 Learning Exercises

### Exercise 1: Compare Serial vs Parallel

Run the simulation twice and compare results:

```bash
# Run 1: Current (parallel) workflow
uv run python main.py --duration 240 --patients 15 --output parallel_run

# Check results/parallel_run_summary.csv
# Note the magnet_busy_pct
```

### Exercise 2: Stress Test

What happens with more patients?

```bash
uv run python main.py --duration 480 --patients 30 --output stress_test
```

Watch the **gowned waiting** area. Does it fill up?

### Exercise 3: Data Analysis

```python
import pandas as pd

# Load movement data
movements = pd.read_csv('results/mri_digital_twin_movements.csv')

# How long do patients spend in each zone?
zone_times = movements.groupby('patient_id').apply(
    lambda x: x.groupby('zone')['timestamp'].diff().mean()
)
print(zone_times)
```

## 📚 Next Steps

1. **Modify the workflow**: Edit `src/core/workflow.py` to change patient flow
2. **Adjust staffing**: Edit `src/config.py` → `STAFF_COUNT`
3. **Change room layout**: Edit `src/config.py` → `ROOM_COORDINATES`
4. **Add new metrics**: Edit `src/analysis/tracker.py`

## 🆘 Getting Help

If you encounter issues:

1. Check the console output for error messages
2. Verify Python version: `python --version`
3. Verify dependencies: `uv run python -c "import simpy, pygame, pandas"`
4. Check `extra/` folder for legacy implementations

## 🎉 Success Checklist

- [ ] PyGame window opens
- [ ] Patients (circles) appear and move
- [ ] Staff (triangles/squares) move around
- [ ] Patients change colors (grey → blue → yellow → green)
- [ ] Simulation completes without errors
- [ ] Reports generated in `results/` folder
- [ ] Summary shows throughput and utilization metrics

**Congratulations!** You've successfully run the MRI Digital Twin simulation! 🎊
