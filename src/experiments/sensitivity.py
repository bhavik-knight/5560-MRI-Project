import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def run_sensitivity_analysis():
    print("=== SENSITIVITY ANALYSIS (DEMAND STRESS TEST) ===")
    
    scenarios = [
        {'demand': 1.0, 'mode': 'baseline', 'label': 'Baseline (100% Demand)'},
        {'demand': 1.0, 'mode': 'singles', 'label': 'Singles Line (100% Demand)'},
        {'demand': 1.2, 'mode': 'baseline', 'label': 'Baseline (120% Demand)'},
        {'demand': 1.2, 'mode': 'singles', 'label': 'Singles Line (120% Demand)'},
        {'demand': 1.5, 'mode': 'baseline', 'label': 'Baseline (150% Demand)'},
        {'demand': 1.5, 'mode': 'singles', 'label': 'Singles Line (150% Demand)'}
    ]
    
    results_map = []
    
    for sc in scenarios:
        d = sc['demand']
        mode_flag = "--singles-line" if sc['mode'] == 'singles' else ""
        print(f"\nrunning: {sc['label']}")
        
        cmd = f"uv run main.py --mode batch --sims 50 --epochs 1 --demand {d} {mode_flag} > /dev/null"
        exit_code = os.system(cmd)
        
        if exit_code != 0:
            print(f"Error executing {sc['label']}")
            continue
            
        # Read result (last run)
        df = pd.read_csv("results/magnet_performance.csv")
        green_mins = df['Scan_Value_Added'].mean()
        util_pct = (green_mins / (720 * 2)) * 100
        
        results_map.append({
            'Scenario': sc['label'],
            'Demand': f"{int(d*100)}%",
            'Strategy': "Singles Line" if sc['mode'] == 'singles' else "Standard",
            'Utilization (%)': util_pct,
            'Productive Minutes': green_mins
        })
        
    # Analysis
    res_df = pd.DataFrame(results_map)
    print("\n=== RESULTS TABLE ===")
    print(res_df[['Demand', 'Strategy', 'Utilization (%)']])
    
    # Store
    res_df.to_csv('results/sensitivity_analysis_raw.csv', index=False)
    
    # Plot
    plt.figure(figsize=(10, 6))
    sns.set_context("talk")
    sns.set_style("whitegrid")
    
    ax = sns.barplot(x='Demand', y='Utilization (%)', hue='Strategy', data=res_df, palette=['grey', '#2ecc71'])
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f%%', padding=3)

    plt.title("Sensitivity Analysis: Singles Line Effectiveness vs Demand", pad=20)
    plt.ylim(0, 100)
    plt.ylabel("Magnet Utilization (Productive %)")
    
    outfile = "results/plots/sensitivity_analysis.png"
    os.makedirs('results/plots', exist_ok=True)
    plt.savefig(outfile)
    print(f"Saved: {outfile}")

if __name__ == "__main__":
    run_sensitivity_analysis()
