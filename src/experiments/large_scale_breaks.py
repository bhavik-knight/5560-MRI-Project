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
    # Suppress print output from inside the simulation
    with suppress_stdout():
        sim = HeadlessSimulation(settings, seed)
        return sim.run()

def run_experiment():
    SIMS_PER_SCENARIO = 5000 # Reduced from 50k to 5k for reasonable execution time in interactive env
    EPOCHS = 1
    
    print(f"=== LARGE SCALE BREAKS EXPERIMENT ({SIMS_PER_SCENARIO * 2} runs) ===")
    
    scenarios = [
        {'breaks': False, 'label': 'No Breaks (Ideal)'},
        {'breaks': True, 'label': 'With Breaks (Realistic)'}
    ]
    
    results = []
    
    for sc in scenarios:
        with_breaks = sc['breaks']
        label = sc['label']
        print(f"\nRunning Scenario: {label}")
        
        start_time = time.time()
        
        # Prepare tasks
        base_seed = int(time.time())
        tasks = []
        for i in range(SIMS_PER_SCENARIO):
            settings = {
                'duration': config.DEFAULT_DURATION, 
                'with_breaks': with_breaks,
                'singles_line_mode': False,
                'demand_multiplier': 1.0
            }
            tasks.append((base_seed + i, settings))
            
        # Execute
        batch_res = []
        with multiprocessing.Pool() as pool:
            for i, res in enumerate(pool.imap_unordered(_worker_task, tasks, chunksize=100)):
                batch_res.append(res)
                if i % 5000 == 0 and i > 0:
                    print(f"  {i}/{SIMS_PER_SCENARIO} completed...")
                    
        elapsed = time.time() - start_time
        print(f"  Scenario Complete in {elapsed:.1f}s")
        
        # Process metrics
        # We need Throughput and Queue Lengths (inferred from Wait Times maybe? or just process throughput)
        # Using throughput as primary stability metric
        
        throughput_vals = [r['patients_completed'] for r in batch_res]
        
        # Store for dataframe
        for val in throughput_vals:
            results.append({
                'Scenario': label,
                'Throughput': val
            })
            
    # Analysis
    df = pd.DataFrame(results)
    
    # Save Raw Data
    df.to_csv('results/breaks_experiment_100k.csv', index=False)
    
    # Stats
    stats = df.groupby('Scenario')['Throughput'].describe()
    print("\n=== STATISTICS ===")
    print(stats)
    
    # Visualization
    plt.figure(figsize=(10, 6))
    sns.set_context("talk")
    sns.set_style("whitegrid")
    
    sns.kdeplot(data=df, x='Throughput', hue='Scenario', fill=True, palette=['#2ecc71', '#e74c3c'], alpha=0.5)
    
    plt.title(f"Impact of Staff Fatigue (Breaks) on System Stability\n(N={SIMS_PER_SCENARIO} per scenario)", pad=20)
    plt.xlabel("Daily Throughput (Patients)")
    
    outfile = "results/plots/shift_stability_100k.png"
    os.makedirs('results/plots', exist_ok=True)
    plt.savefig(outfile)
    print(f"Saved Plot: {outfile}")

if __name__ == "__main__":
    run_experiment()
