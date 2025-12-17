# MRI Digital Twin - Modular Architecture

A real-time agent-based simulation of an MRI department workflow, demonstrating the efficiency gains of parallel processing ("Pit Crew" model) over traditional serial workflows.

## 🎯 Project Overview

This digital twin simulates patient flow through an MRI suite, visualizing:
- **Patient movement** through zones (waiting → changing → prep → scanning → exit)
- **Staff coordination** (porters, backup techs, scan techs)
- **Resource utilization** (magnets, prep rooms, gowned waiting buffer)
- **The "Utilization Paradox"** - distinguishing busy time (value-added) from occupied time

## 🏗️ Modular Architecture

```
mri-project/
├── src/
│   ├── config.py           # Centralized constants & coordinates
│   ├── visuals/            # PyGame visualization
│   │   ├── layout.py       # Static floor plan rendering
│   │   ├── sprites.py      # Agent classes (Patient, Staff)
│   │   └── renderer.py     # Window manager
│   ├── analysis/           # Statistics & reporting
│   │   ├── tracker.py      # SimStats observer
│   │   └── reporter.py     # CSV export & reports
│   └── core/               # SimPy simulation logic
│       ├── workflow.py     # Patient journey process
│       └── engine.py       # Main simulation loop
├── main.py                 # Entry point
├── extra/                  # Legacy files (old implementations)
└── results/                # Generated reports & data
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- `uv` package manager (recommended) or `pip`

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd mri-project

# Install dependencies with uv
uv sync

# Or with pip
pip install -r requirements.txt
```

### Running the Simulation

**Default run (120 minutes, 10 patients):**
```bash
uv run python main.py
```

**Custom parameters:**
```bash
# Quick test (60 min, 5 patients)
uv run python main.py --duration 60 --patients 5

# Full day simulation (8 hours, 20 patients)
uv run python main.py --duration 480 --patients 20

# Specify output directory
uv run python main.py --output my_results
```

### What You'll See

1. **PyGame Window**: Real-time visualization showing:
   - Color-coded rooms (change rooms, prep rooms, magnets)
   - Moving agents:
     - 🔘 **Circles** = Patients (color changes with state)
     - 🔶 **Triangles** = Porters (orange)
     - 🟦 **Squares** = Techs (cyan/purple)
   - Simulation time display

2. **Console Output**: Live statistics and progress

3. **Generated Reports** (in `results/` folder):
   - `*_movements.csv` - All patient movements
   - `*_states.csv` - State transition log
   - `*_gowned_waiting.csv` - Buffer usage data
   - `*_summary.csv` - Key metrics
   - `*_report.txt` - Human-readable summary

## 📊 Key Metrics

The simulation tracks the **"Utilization Paradox"**:

- **Magnet Busy %** (Value-Added): Time actually scanning
- **Magnet Occupied %**: Total time in use (prep + scan in serial)
- **Magnet Idle %**: True idle time

**Insight**: In serial workflow, high occupied % looks good but hides low efficiency. In parallel workflow, the magnet focuses on scanning (higher busy %).

## 🎨 Visual Legend

### Patient States (Circle Colors)
- 🔘 **Grey** - Arriving (Zone 1)
- 🔵 **Teal** - Changing (Change rooms)
- 🟡 **Yellow** - Prepped (Gowned waiting buffer)
- 🟢 **Green** - Scanning (Magnet)

### Staff Roles
- 🔶 **Orange Triangle** - Porter (transports patients)
- 🟦 **Cyan Square** - Backup Tech (preps patients)
- 🟪 **Purple Square** - Scan Tech (operates magnet)

### Zones
- **Zone 1** (Grey) - Public corridor / waiting
- **Zone 2** (Various) - The Hub (change, prep, gowned waiting)
- **Zone 3** (Dark Grey) - Control rooms
- **Zone 4** (Cyan) - MRI magnets (3T and 1.5T)

## 🔬 Workflow Simulation

The simulation implements a realistic patient journey:

1. **Arrival** → Patient appears in Zone 1
2. **Transport** → Porter escorts to change room
3. **Changing** → Patient changes into gown (~3.5 min)
4. **Prep** → Backup tech performs IV setup (~2.5 min)
5. **Gowned Waiting** → Patient waits in buffer (yellow state)
6. **Scanning** → Scan tech operates magnet (~22 min)
7. **Exit** → Patient leaves system

## 📈 Data Analysis

All simulation data is exported to CSV for further analysis:

```python
# Example: Load and analyze results
import pandas as pd

summary = pd.read_csv('results/mri_digital_twin_summary.csv')
print(f"Throughput: {summary['throughput'].values[0]} patients")
print(f"Magnet Busy: {summary['magnet_busy_pct'].values[0]}%")
```

## 🛠️ Development

### Project Structure

- **`src/config.py`**: All constants (no dependencies)
- **`src/visuals/`**: Pure rendering (no simulation logic)
- **`src/analysis/`**: Observer pattern for stats (no rendering)
- **`src/core/`**: SimPy processes (coordinates others)

### Key Design Patterns

- **Separation of Concerns**: Each module has single responsibility
- **Observer Pattern**: Stats tracking doesn't clutter simulation
- **Bridge Pattern**: Engine connects SimPy and PyGame
- **No Circular Dependencies**: Clean import hierarchy

## 📚 References

This simulation is based on empirical data from:
- MRI department efficiency studies
- GE iCenter analytics
- Workflow optimization research

## 🤝 Contributing

See `extra/` folder for legacy implementations and development history.

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

Built with:
- **SimPy** - Discrete-event simulation
- **PyGame** - Real-time visualization
- **Pandas** - Data analysis
- **Plotly** - Interactive charts (in Streamlit dashboard)
