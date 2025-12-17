# Extra Files - Legacy Implementations

This folder contains previous implementations and development artifacts that are no longer part of the main modular architecture.

## Contents

### Old Implementations
- **`digital_twin.py`** - Original monolithic PyGame + SimPy implementation
- **`simulation.py`** - Early simulation logic (pre-refactor)
- **`app.py`** - Streamlit dashboard (still functional, separate from main simulation)
- **`entities.py`** - Old Patient class implementation
- **`engine.py`** - Original simulation engine
- **`resources.py`** - Old resource definitions
- **`collect_data.py`** - Batch data collection script

## Why These Were Moved

The project was refactored into a modular architecture with clear separation of concerns:

- **Visualization** → `src/visuals/`
- **Simulation Logic** → `src/core/`
- **Statistics** → `src/analysis/`
- **Configuration** → `src/config.py`

The old files mixed these concerns, making them harder to maintain and extend.

## Still Useful?

### Streamlit Dashboard (`app.py`)

The Streamlit dashboard is still functional and provides a different view of the simulation:

```bash
uv run streamlit run extra/app.py
```

This gives you:
- Interactive parameter controls
- Gantt charts of patient flow
- Plotly visualizations
- Sensitivity analysis

### Data Collection (`collect_data.py`)

For batch experiments:

```bash
uv run python extra/collect_data.py
```

## Development History

These files represent the evolution of the project:

1. **Phase 1**: Monolithic `simulation.py` (all logic in one file)
2. **Phase 2**: Split into entities, engine, resources
3. **Phase 3**: Added PyGame visualization (`digital_twin.py`)
4. **Phase 4**: Modular refactoring (current `src/` structure)

## Reference

Keep these files for:
- Understanding the development process
- Comparing old vs new implementations
- Extracting useful code snippets
- Historical documentation
