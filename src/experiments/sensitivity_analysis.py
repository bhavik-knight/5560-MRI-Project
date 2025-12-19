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
        sim = HeadlessSimulation(settings, seed)
        return sim.run()

def run_experiment():
    SIMS = 50 # Per scenario per Prompt
    PROBS = [0.0, 0.05, 0.10, 0.15, 0.20] # 0% to 20%
    print(f"=== SENSITIVITY ANALYSIS: COMPLIANCE (N={SIMS}/scenario) ===")
    
    results = []
    
    for prob in PROBS:
        print(f"\nRunning No-Show Rate: {prob:.2f} ({prob*100:.0f}%)")
        
        # Prepare tasks
        base_seed = int(time.time())
        tasks = []
        for i in range(SIMS):
            settings = {
                'duration': config.DEFAULT_DURATION,
                'no_show_prob': prob,
                'demand_multiplier': 1.0 # 100% Demand
            }
            tasks.append((base_seed + i, settings))
            
        # Execute
        batch_res = []
        with multiprocessing.Pool() as pool:
            for res in pool.imap_unordered(_worker_task, tasks):
                batch_res.append(res)
                
        # Aggregate
        for r in batch_res:
            res_entry = {
                'No_Show_Rate': prob,
                'Throughput': r['patients_completed'],
                'Magnet_Idle_Pct': 0.0 # Calculate below
            }
            
            # Calculate Magnet Idle % (Aggregated for both magnets?)
            # Formula: (IdleTime3T + IdleTime1.5T) / (Duration * 2)
            # Check keys
            idle_3t = r.get('magnet_3t_idle', 0.0)
            idle_15t = r.get('magnet_15t_idle', 0.0)
            duration = r['duration']
            
            idle_pct = ((idle_3t + idle_15t) / (duration * 2)) * 100
            res_entry['Magnet_Idle_Pct'] = idle_pct
            
            results.append(res_entry)
            
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Save Raw Data
    os.makedirs('results', exist_ok=True)
    df.to_csv('results/sensitivity_compliance_raw.csv', index=False)
    print("\nSaved raw data to results/sensitivity_compliance_raw.csv")
    
    # Analysis
    summary = df.groupby('No_Show_Rate')[['Throughput', 'Magnet_Idle_Pct']].describe()
    print("\n=== SENSITIVITY RESULTS ===")
    print(summary)
    
    # Visualization: Dual Axis Plot? Or Facet?
    # Relationship: X=NoShowRate, Y1=Throughput, Y2=IdlePct
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    sns.set_context("talk")
    sns.set_style("whitegrid")
    
    # Plot Throughput (Left Axis)
    sns.lineplot(data=df, x='No_Show_Rate', y='Throughput', errorbar='sd', marker='o', ax=ax1, color='#2c3e50', label='Throughput')
    ax1.set_ylabel('Patients Processed (Mean ± SD)')
    ax1.set_xlabel('No-Show Probability')
    ax1.set_ylim(bottom=0)
    
    # Plot Idle % (Right Axis)
    ax2 = ax1.twinx()
    sns.lineplot(data=df, x='No_Show_Rate', y='Magnet_Idle_Pct', errorbar='sd', marker='s', ax=ax2, color='#e74c3c', label='Magnet Idle %')
    ax2.set_ylabel('Magnet Idle Time (%)', color='#e74c3c')
    ax2.tick_params(axis='y', labelcolor='#e74c3c')
    ax2.set_ylim(bottom=0)
    
    plt.title("Impact of Patient Compliance (No-Shows) on System Efficiency", pad=20)
    
    # Legend
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc='center right')
    ax1.get_legend().remove()
    
    outfile = "results/plots/sensitivity_compliance.png"
    os.makedirs('results/plots', exist_ok=True)
    plt.savefig(outfile)
    print(f"Saved Plot: {outfile}")

if __name__ == "__main__":
    run_experiment()
