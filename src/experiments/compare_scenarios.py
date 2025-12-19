import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def run_experiment():
    print("=== SINGLES LINE EXPERIMENT ===")
    
    # 1. Baseline Run
    print("\n[1/2] Running Baseline Scenario...")
    # Use standard batch command
    exit_code = os.system("uv run main.py --mode batch --sims 50 --epochs 1")
    if exit_code != 0:
        print("Error in Baseline Run")
        return
        
    shutil.move("results/magnet_performance.csv", "results/magnet_performance_baseline.csv")
    
    # 2. Singles Line Run
    print("\n[2/2] Running Singles Line Scenario...")
    exit_code = os.system("uv run main.py --mode batch --sims 50 --epochs 1 --singles-line")
    if exit_code != 0:
        print("Error in Singles Line Run")
        return
        
    shutil.move("results/magnet_performance.csv", "results/magnet_performance_singles.csv")
    
    # 3. Analyze Results
    print("\n=== ANALYSIS ===")
    
    df_base = pd.read_csv("results/magnet_performance_baseline.csv")
    df_single = pd.read_csv("results/magnet_performance_singles.csv")
    
    # Calculate Metrics
    # Metric 1: Productive Time (Green)
    base_green = df_base['Scan_Value_Added'].mean()
    single_green = df_single['Scan_Value_Added'].mean()
    
    # Metric 2: Utilization % (Capacity = 1440 mins total per run)
    TOTAL_CAPACITY = 720 * 2
    base_util = (base_green / TOTAL_CAPACITY) * 100
    single_util = (single_green / TOTAL_CAPACITY) * 100
    
    delta_util = single_util - base_util
    pct_change = ((single_green - base_green) / base_green) * 100
    
    print(f"Baseline Productivity:    {base_green:.1f} mins ({base_util:.1f}%)")
    print(f"Singles Line Productivity: {single_green:.1f} mins ({single_util:.1f}%)")
    print(f"Impact: {delta_util:+.2f}% utilization (+{pct_change:.1f}% volume)")
    
    # 4. Visualization
    data = [
        {'Scenario': 'Baseline', 'Productive Utilization (%)': base_util},
        {'Scenario': 'Singles Line', 'Productive Utilization (%)': single_util}
    ]
    viz_df = pd.DataFrame(data)
    
    plt.figure(figsize=(8, 6))
    sns.set_context("talk")
    sns.set_style("whitegrid")
    
    ax = sns.barplot(x='Scenario', y='Productive Utilization (%)', data=viz_df, palette=['grey', '#2ecc71'])
    ax.bar_label(ax.containers[0], fmt='%.1f%%', padding=3)
    
    plt.title(f"Impact of Singles Line Strategy\n(Dynamic Gap Filling)", pad=20)
    plt.ylim(0, 100)
    
    outfile = "results/plots/singles_line_impact.png"
    os.makedirs('results/plots', exist_ok=True)
    plt.savefig(outfile)
    print(f"Saved Comparison Plot: {outfile}")

if __name__ == "__main__":
    run_experiment()
