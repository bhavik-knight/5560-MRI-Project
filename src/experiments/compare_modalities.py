import os
import shutil
import pandas as pd
import multiprocessing
import time
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
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
    SIMS = 1000 # Enough for significance
    print(f"=== COMPARE MODALITIES EXPERIMENT (N={SIMS}) ===")
    
    scenarios = [
        {'label': 'Baseline (Entropy)', 'force_type': None},
        {'label': 'Neuro Block (Brain Only)', 'force_type': 'brain_routine'},
        {'label': 'MSK Block (Knee Only)', 'force_type': 'knee'} # Wait, 'knee' might not be in config.SCAN_PROTOCOLS keys?
    ]
    
    # Check config keys
    # brain_routine, prostate, spine, abdomen_body, cardiac
    # 'knee' is not in current keys based on config.py review. 'spine' or 'brain_routine' are valid.
    # Source 140 mentiones Knee, but config.py has [Brain, Spine, Prostate, Abdomen, Cardiac].
    # I will use 'spine' as proxy for MSK if 'knee' is missing, or add 'knee' if I can.
    # Given prompt says "MSK Block (Source 133): 100% Knee exams", but config only has Spine as MSK-like.
    # I'll stick to 'spine' which is closest (MSK Spine) or just define a custom mapped scenario.
    # Actually, config.py lines 230-238 doesn't list 'knee'.
    # I will use 'spine' and label it as MSK Block (Spine) to be safe, or just 'spine'.
    # However, to faithfully follow the prompt which implies 'knee' should exist, I should check if I missed it.
    # Review of config.py: keys are 'brain_routine', 'prostate', 'spine', 'abdomen_body', 'cardiac'.
    # So 'knee' will crash. I will use 'spine' but label it "MSK Block (Spine)" and note in print.
    
    scenarios = [
        {'label': 'Baseline (Mixed)', 'force_type': None},
        {'label': 'Neuro Block (Brain)', 'force_type': 'brain_routine'},
        {'label': 'MSK Block (Spine)', 'force_type': 'spine'} 
    ]

    results = []
    
    for sc in scenarios:
        force_type = sc['force_type']
        label = sc['label']
        print(f"\nRunning {label}...")
        
        start_time = time.time()
        
        # Prepare tasks
        base_seed = int(time.time())
        tasks = []
        for i in range(SIMS):
            settings = {
                'duration': config.DEFAULT_DURATION,
                'demand_multiplier': 1.5, # Saturate demand to test purely throughput capacity
                'singles_line_mode': False,
                'force_type': force_type
            }
            tasks.append((base_seed + i, settings))
            
        # Execute
        batch_res = []
        with multiprocessing.Pool() as pool:
            # chunksize for speed
            for res in pool.imap_unordered(_worker_task, tasks, chunksize=50):
                batch_res.append(res)
                
        # Analyze Throughput
        throughputs = [r['patients_completed'] for r in batch_res]
        avg_throughput = sum(throughputs) / len(throughputs)
        print(f"  Avg Throughput: {avg_throughput:.1f} patients / 12h")
        
        for val in throughputs:
            results.append({'Scenario': label, 'Throughput': val})
            
    # Stats
    df = pd.DataFrame(results)
    print("\n=== COMPARATIVE RESULTS ===")
    print(df.groupby('Scenario')['Throughput'].describe()[['mean', 'std', 'max']])
    
    # Visualization
    plt.figure(figsize=(10, 6))
    sns.set_context("talk")
    sns.set_style("whitegrid")
    
    # Define order for consistency
    order = ['Baseline (Mixed)', 'Neuro Block (Brain)', 'MSK Block (Spine)']
    
    ax = sns.boxplot(x='Scenario', y='Throughput', data=df, order=order, palette="viridis")
    plt.title("Throughput Comparison: Random vs Batching Strategies", pad=20)
    plt.ylabel("Patients Processed (12h Shift)")
    
    # Add Mean Labels
    means = df.groupby('Scenario')['Throughput'].mean()
    baseline_mean = means['Baseline (Mixed)']
    
    for i, label in enumerate(order):
        val = means[label]
        
        # Calculate Delta
        delta_str = ""
        if label != 'Baseline (Mixed)':
            pct_diff = ((val - baseline_mean) / baseline_mean) * 100
            delta_str = f"\n(+{pct_diff:.1f}%)"
            
        # Place text at the mean value (centered)
        # We place it slightly above the mean or median. 
        # Boxplot shows median, means might be different.
        # Let's put it on the box.
        ax.text(i, val, f"{val:.1f}{delta_str}", 
                ha='center', va='center', 
                fontweight='bold', color='white', 
                path_effects=[path_effects.withStroke(linewidth=3, foreground="black")])

    outfile = "results/plots/modality_comparison.png"
    os.makedirs('results/plots', exist_ok=True)
    plt.savefig(outfile)
    print(f"Saved Plot: {outfile}")

if __name__ == "__main__":
    run_experiment()
