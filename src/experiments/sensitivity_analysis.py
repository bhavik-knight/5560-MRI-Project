import os
import shutil
import pandas as pd
import multiprocessing
import time
import matplotlib.pyplot as plt
import seaborn as sns
import contextlib
import sys
from src.core.headless import HeadlessSimulation
import src.config as config

# --- HELPER FOR SUPPRESSING OUTPUT ---
@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout

def _worker_task(seed_and_settings):
    seed, settings = seed_and_settings
    with suppress_stdout():
        # HeadlessSimulation will use params from settings
        # We need to make sure HeadlessSimulation respects 'demand_multiplier' and 'singles_line_mode'
        sim = HeadlessSimulation(settings, seed)
        return sim.run()

def run_experiment():
    SIMS = 100 # Adjust to 500 later if needed, starting with 100 for speed
    DEMANDS = [1.0, 1.2, 1.5] # 100%, 120%, 150%
    STRATEGIES = ['Standard', 'Singles Line']
    
    print(f"=== SENSITIVITY ANALYSIS: DEMAND vs STRATEGY (N={SIMS}/scenario) ===")
    
    results = []
    
    for demand in DEMANDS:
        for strat in STRATEGIES:
            print(f"\nRunning Demand: {demand*100:.0f}% | Strategy: {strat}")
            
            is_singles = (strat == 'Singles Line')
            
            # Prepare tasks
            base_seed = int(time.time())
            tasks = []
            for i in range(SIMS):
                settings = {
                    'duration': config.DEFAULT_DURATION,
                    'demand_multiplier': demand,
                    'singles_line_mode': is_singles,
                    'no_show_prob': config.PROB_NO_SHOW # Keep default
                }
                tasks.append((base_seed + i + (1000 if is_singles else 0), settings))
                
            # Execute
            batch_res = []
            with multiprocessing.Pool() as pool:
                for res in pool.imap_unordered(_worker_task, tasks):
                    batch_res.append(res)
                    
            # Aggregate
            for r in batch_res:
                # Calculate Utilization
                # We want Productive Utilization? Or Occupied?
                # The report says "Utilization". Usually this means Occupied (Busy + Overhead).
                # But let's check what 'magnet_util_pct' in results gives.
                # r['magnet_util_pct'] likely returns Occupied %.
                # Let's verify how HeadlessSimulation constructs this.
                # Tracker calculates busy/occupied/idle.
                # HeadlessSimulation.run returns a dict.
                
                # Re-calculate cleanly here if needed or trust return.
                # Assuming 'magnet_metrics' in r has total times.
                
                # Extract aggregated times
                # Headless returns 'magnet_metrics' which is a dict of total times per magnet or aggregated?
                # Let's inspect tracker.py logic or headless return.
                # Headless.run() returns:
                # { ..., 'magnet_metrics': stats.magnet_metrics (Wait, tracker has magnets dict), ... }
                # Actually, metrics might be flattened.
                
                # Let's rely on standard 'utilization_occupied' if available or manual calc.
                # Tracker.calculate_utilization returns { 'magnet_occupied_pct': ... }
                util_stats = r.get('utilization', {})
                occ_pct = util_stats.get('magnet_occupied_pct', 0.0)
                
                res_entry = {
                    'Demand Level': f"{int(demand*100)}%",
                    'Strategy': strat,
                    'Utilization (%)': occ_pct
                }
                results.append(res_entry)
                
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Save Raw Data
    os.makedirs('results', exist_ok=True)
    df.to_csv('results/sensitivity_demand_raw.csv', index=False)
    
    # Analysis Summary
    summary = df.groupby(['Demand Level', 'Strategy'])['Utilization (%)'].describe()
    print("\n=== SENSITIVITY RESULTS ===")
    print(summary)
    
    # Visualization
    plt.figure(figsize=(10, 6))
    sns.set_context("talk")
    sns.set_style("whitegrid")
    
    # Custom palette: Standard=Grey, Singles Line=Green
    palette = {'Standard': '#95a5a6', 'Singles Line': '#2ecc71'}
    
    ax = sns.barplot(x='Demand Level', y='Utilization (%)', hue='Strategy', data=df, palette=palette, errorbar='sd')
    
    # Add Value Labels
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f%%', padding=3, size=12)
        
    plt.title("Impact of 'Singles Line' Strategy by Demand Level\n(15-Hour Shift - Occupied Utilization)", pad=20)
    plt.ylim(0, 100)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    
    plt.tight_layout()
    outfile = "results/plots/sensitivity_analysis.png"
    plt.savefig(outfile)
    print(f"Saved Plot: {outfile}")

if __name__ == "__main__":
    run_experiment()
