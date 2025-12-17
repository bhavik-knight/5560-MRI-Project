# MRI Digital Twin: Agent-Based Process Simulation

**A discrete-event simulation demonstrating the "Utilization Paradox" in MRI department workflows**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Project Overview

This digital twin simulates a 12-hour MRI department shift using agent-based modeling to demonstrate the efficiency gains of **parallel processing** ("Pit Crew" model) over traditional **serial workflows**.

### The "Utilization Paradox"

Traditional MRI departments show high equipment "occupied time" (92%) but hide critically low "value-added time" (22%):

| Metric | Serial Workflow | Parallel Workflow |
|--------|----------------|-------------------|
| **Occupied Time** | 92% | 75% |
| **Busy Time (Value-Added)** | 22% | 73% |
| **Interpretation** | Looks efficient, is wasteful | Lower occupied %, 3.3x more productive |

**Root Cause:** In serial workflows, patient prep happens *inside* the magnet room, wasting expensive equipment time on low-value tasks.

**Solution:** The "Pit Crew" model moves prep outside, using a **gowned waiting buffer** to stage prepped patients, allowing the magnet to focus exclusively on scanning.

## Architecture

```
mri-project/
├── src/
│   ├── config.py              # Centralized constants (NO dependencies)
│   │   ├── Visual constants   # 1600×800 medical white aesthetic
│   │   ├── Room coordinates   # 13 rooms, 80/20 layout
│   │   ├── Process times      # Triangular distributions (empirical data)
│   │   └── Probabilities      # IV needs: 70%, difficult: 15%
│   │
│   ├── core/                  # SimPy Discrete-Event Engine
│   │   ├── engine.py          # Main simulation loop (bridges SimPy + PyGame)
│   │   └── workflow.py        # Patient journey (7-step process)
│   │
│   ├── visuals/               # PyGame "Medical White" Renderer
│   │   ├── layout.py          # Static floor plan (white rooms, grey corridors)
│   │   ├── sprites.py         # Agent classes (Patient, Staff)
│   │   └── renderer.py        # Window manager (1200px sim + 400px sidebar)
│   │
│   └── analysis/              # Statistical Tracker (Observer Pattern)
│       ├── tracker.py         # SimStats (logs movements, states, utilization)
│       └── reporter.py        # CSV export, text reports
│
├── main.py                    # Entry point
├── README.md                  # This file
├── WALKTHROUGH.md             # Comprehensive technical documentation
└── results/                   # Generated simulation data
```

### Design Patterns

- **Separation of Concerns**: Each module has single responsibility
- **Observer Pattern**: Stats tracking doesn't clutter simulation
- **Bridge Pattern**: Engine connects SimPy (discrete-event) and PyGame (real-time)
- **No Circular Dependencies**: Clean import hierarchy

## Key Features

### 1. Time-Based Simulation (Process Management Best Practice)
- **Shift Duration**: 720 minutes (12 hours)
- **Warm-Up Period**: 60 minutes (excluded from statistics to remove empty-system bias)
- **Data Collection**: 660 minutes of steady-state operation

### 2. Real-Time Visualization
- **Medical White Aesthetic**: High-contrast white rooms on grey background
- **80/20 Layout**: 1200px simulation area + 400px sidebar
- **Smooth Animation**: 60 FPS with agent movement at 5-6 pixels/frame
- **Live Statistics**: Real-time throughput, utilization, and queue metrics

### 3. Comprehensive Data Collection
- Patient movement logs (zone transitions)
- State change logs (arriving → changing → prepped → scanning)
- Gowned waiting buffer usage
- Magnet utilization (busy vs occupied time)
- Summary statistics (CSV + text reports)

### 4. Empirical Process Times
All durations based on real MRI department data:
- Screening: triangular(2, 3, 5) minutes
- Changing: triangular(2, 3.5, 5) minutes
- IV Setup: triangular(1, 2.5, 4) minutes
- Scanning: triangular(18, 22, 26) minutes

## Reproduction Instructions

### Prerequisites
- Python 3.12 or higher
- `uv` package manager ([installation](https://github.com/astral-sh/uv))

### Installation

```bash
# Clone repository
git clone <repository-url>
cd mri-project

# Install dependencies (includes opencv-python for video recording)
uv sync
```

### Running the Simulation

**Default 12-hour shift:**
```bash
uv run python main.py
```

**Custom duration:**
```bash
uv run python main.py --duration 120    # 2 hour test
uv run python main.py --duration 360    # 6 hour shift
```

**With video recording:**
```bash
uv run python main.py --record          # Generates simulation_video.mp4
```

### What to Expect

**Simulation Duration:**
- Total runtime: 780 minutes (60 warm-up + 720 data collection)
- Real-time duration: ~6.5 minutes (with SIM_SPEED = 0.5)
- Video length: ~6.5 minutes (if recording)

**Visual Output:**
- PyGame window (1600×800) with animated agents
- Patients (circles) change color by state:
  - Grey → Arriving
  - Teal → Changing
  - Yellow → Prepped (waiting)
  - Green → Scanning
- Staff (triangles/squares) escort patients

**Data Output (in `results/` folder):**
- `*_movements.csv` - All patient zone transitions
- `*_states.csv` - State change log
- `*_gowned_waiting.csv` - Buffer usage
- `*_summary.csv` - Key performance indicators
- `*_report.txt` - Human-readable analysis

## Key Metrics

### Throughput
- Number of patients who completed scans during shift
- Expected: ~22-24 patients per 12-hour shift

### Magnet Utilization
- **Busy %**: Time actually scanning (value-added work)
- **Occupied %**: Total time in use (includes prep in serial workflow)
- **Idle %**: True idle time

### Buffer Performance
- Average wait time in gowned waiting
- Maximum wait time
- Demonstrates decoupling effect

## Technical Details

### Simulation Parameters
```python
DEFAULT_DURATION = 720      # 12 hours
WARM_UP_DURATION = 60       # 1 hour
SIM_SPEED = 0.5             # 1 sim minute = 0.5 real seconds
FPS = 60                    # Smooth animation
```

### Agent Movement
- Smooth interpolation between positions
- Patient speed: 5 pixels/frame
- Staff speed: 6 pixels/frame
- Movement checks: every 0.01 sim minutes

### Time Advancement
```python
delta_sim_time = (1.0 / FPS) * (60 / SIM_SPEED) / 60
# = 0.0333 sim minutes per frame
# = 2 sim seconds per frame
```

## Validation

### Visual Verification
Watch for these behaviors:
- ✓ Patients spawn in Zone 1 (bottom)
- ✓ Orange triangle (porter) escorts to change rooms
- ✓ Patients turn teal while changing
- ✓ Cyan square (backup tech) escorts to prep
- ✓ Patients turn yellow in gowned waiting
- ✓ Purple square (scan tech) escorts to magnet
- ✓ Patients turn green while scanning
- ✓ Patients exit to the right

### Data Verification
```python
import pandas as pd

# Load summary
summary = pd.read_csv('results/mri_digital_twin_summary.csv')
print(f"Throughput: {summary['throughput'].values[0]} patients")
print(f"Magnet Busy: {summary['magnet_busy_pct'].values[0]}%")
```

## Documentation

- **README.md** (this file): Quick start and overview
- **WALKTHROUGH.md**: Comprehensive technical documentation for report writing
  - 17 sections covering architecture, implementation, validation
  - Code snippets, formulas, and examples
  - Report writing guide with suggested structure

## Citation

If you use this simulation in your research, please cite:

```bibtex
@software{mri_digital_twin,
  title = {MRI Digital Twin: Agent-Based Process Simulation},
  author = {[Your Name]},
  year = {2025},
  url = {[Repository URL]}
}
```

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Process times based on GE iCenter analytics
- Workflow design inspired by Formula 1 "Pit Crew" model
- Built with SimPy, PyGame, and Pandas

---

**For detailed technical documentation, see [WALKTHROUGH.md](WALKTHROUGH.md)**
