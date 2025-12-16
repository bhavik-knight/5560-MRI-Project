# MRI Department Efficiency Digital Twin

## Overview
This project is a **Discrete-Event Simulation (DES)** and **Digital Twin** application designed to analyze and optimize the workflow of an MRI department. It models the flow of patients through the facility to identify bottlenecks and test improvements, specifically comparing the **Current State (Serial Processing)** against a proposed **Future State (Parallel Processing / "Pit Crew" Model)**.

The application allows stakeholders to visualize patient flow, conduct sensitivity analysis on staffing levels, and quantify improvements in throughput and magnet utilization.

## Key Features

### 1. Interactive Digital Twin Dashboard
A Streamlit-based web application providing real-time control and visualization:
-   **Sensitivity Analysis**: Adjust staff counts and bed flip times on the fly.
-   **Scenario Toggling**: Switch between "Serial" and "Parallel" workflows to see immediate impacts.
-   **Gantt Chart**: Visualizes magnet usage (Scanning vs. Idle/Prep) over a 12-hour shift.
-   **Spatial Animation**: A "Digital Twin" visualization showing patients moving between zones (Waiting, Prepping, Scanning) in real-time.

### 2. Modular Simulation Engine
Built on `SimPy`, the simulation logic is decoupled into a robust modular architecture:
-   **Data-Driven**: Configuration based on empirical data (distributions for screening, IV setup, scanning, etc.).
-   **Process Modeling**: Accurate representation of resource seizing, task execution, and release.
-   **Spatiotemporal Tracking**: Records not just *what* happens, but *where* patients are at every minute.

### 3. Analytics & Reporting
-   **Throughput Metrics**: Tracks total patients processed per shift.
-   **Resource Utilization**: Calculates "Value-Added" (Scanning) vs. "Non-Value Added" (Idle/Prep) time.
-   **Batch Analysis**: Automated scripts to run multiple iterations (Monte Carlo style) for robust statistical reporting.

## Installation

This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone <repository-url>
cd mri_project

# Install dependencies
uv sync
```

## Usage

### Run the Dashboard
To launch the interactive digital twin:
```bash
uv run streamlit run src/app.py
```

### Run Batch Analysis
To generate statistical reports and CSV data from multiple simulation runs:
```bash
uv run python src/analysis.py
```

### Run Data Collection (Report Scenarios)
To reproduce the specific scenarios for the project report (Baseline vs. Optimization):
```bash
uv run python src/collect_data.py
```

## Project Structure

The codebase follows a modular design pattern in the `src/` directory:

| Module | Description |
| :--- | :--- |
| `config.py` | **Data Layer**. Contains all empirical distributions (Triangular/Normal) and system parameters. |
| `resources.py` | **Physical Layer**. Defines SimPy resources (Magnet, Prep Rooms, Techs, Porters). |
| `entities.py` | **Agent Layer**. Defines the `Patient` class and the state-machine logic for their journey. |
| `engine.py` | **Orchestrator**. Connects agents to resources and runs the simulation loop. |
| `app.py` | **Presentation Layer**. The Streamlit dashboard code. |
| `analysis.py` | **Reporting Layer**. Scripts for batch execution and plotting. |

## Simulation Scenarios

### Scenario A: Current State (Serial)
-   **Workflow**: The magnet room is seized *before* patient preparation begins.
-   **Consequence**: The expensive MRI machine sits idle while the patient is screened, changed, and cannulated inside the room.
-   **Result**: High "Occupancy" but low "Value-Added" utilization.

### Scenario B: Future State (Parallel / Pit Crew)
-   **Workflow**: Patient preparation occurs in a separate "Zone 2" area. The magnet is seized only when the patient is ready to scan.
-   **Consequence**: Magnet idle time is minimized.
-   **Result**: Significantly higher throughput and effective utilization.
