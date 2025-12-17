# MRI Digital Twin Simulation

A real-time visualization of an MRI department workflow demonstrating the efficiency gains of parallel processing over traditional serial workflows.

## Quick Start

### Installation

```bash
# Navigate to project directory
cd mri-project

# Install dependencies
uv sync
```

### Running the Simulation

```bash
# Default run (12 hour shift = 720 minutes)
uv run python main.py

# Quick test (2 hours)
uv run python main.py --duration 120

# Half shift (6 hours)
uv run python main.py --duration 360
```

**Note:** The simulation includes a 1-hour warm-up period to remove empty-system bias. Statistics are collected after the warm-up.

### What You'll See

A PyGame window will open showing:
- **White rooms** with black borders (medical aesthetic)
- **Colored circles** (patients) moving through the facility
- **Triangles and squares** (staff) helping patients
- **Right sidebar** with live statistics and legend

### Understanding the Colors

**Patients (Circles):**
- Grey → Arriving
- Teal → Changing
- Yellow → Waiting (prepped)
- Green → Scanning

**Staff:**
- Orange Triangle → Porter
- Cyan Square → Backup Tech
- Purple Square → Scan Tech

### Results

After the simulation, check the `results/` folder for:
- CSV files with detailed logs
- Summary statistics
- Text report with key findings

## Key Metrics

The simulation tracks the **"Utilization Paradox"**:
- **Magnet Busy %** - Time actually scanning (value-added)
- **Magnet Idle %** - True idle time
- **Throughput** - Patients completed

## Simulation Parameters

- **Default Duration**: 720 minutes (12 hour shift)
- **Warm-Up Period**: 60 minutes (excluded from statistics)
- **Data Collection**: 660 minutes (after warm-up)
- **Patient Arrivals**: Every ~30 minutes until shift ends

## Requirements

- Python 3.12+
- uv package manager

## Troubleshooting

**No animation?** The simulation runs fast - watch for colored circles moving across the screen.

**Window doesn't open?** Make sure pygame is installed: `uv sync`

**Need help?** See `WALKTHROUGH.md` for detailed documentation.

## License

Educational project for MRI workflow optimization research.
