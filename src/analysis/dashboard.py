import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Set style for professional aesthetics
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_context("talk")

def plot_utilization_paradox(run_id=0):
    """
    Source 56, 62: The Utilization Paradox.
    Stacked Bar Chart showing Occupied Time vs Value-Added Time.
    """
    print(f"Generating Utilization Paradox Visualization for Run {run_id}...")
    
    # Load Data (using the summary file we just created)
    df = pd.read_csv('results/magnet_performance.csv')
    
    # Filter for specific run or average
    run_data = df[df['RunID'] == run_id].iloc[0]
    
    # Calculate Idle Time (Total Duration = 720 mins * 2 Magnets = 1440, wait, this is aggregate per run)
    # The csv has aggregate for the whole system (2 magnets combined) in current batch logic
    # Total System Capacity per Run = 720 * 2 = 1440 mins
    total_capacity = 720 * 2
    
    green_time = run_data['Scan_Value_Added']
    brown_time = run_data['Scan_Overhead']
    occupied_time = green_time + brown_time
    idle_time = total_capacity - occupied_time
    if idle_time < 0: idle_time = 0 # Rounding errors
    
    # Create DataFrame for plotting
    plot_data = pd.DataFrame({
        'Category': ['Total Capacity'],
        'Value-Added (Green)': [green_time],
        'Overhead (Brown)': [brown_time],
        'Idle (Grey)': [idle_time]
    })
    
    # Plotting
    fig, ax = plt.subplots(figsize=(10, 6))
    
    plot_data.plot(
        x='Category', 
        y=['Value-Added (Green)', 'Overhead (Brown)', 'Idle (Grey)'], 
        kind='bar', 
        stacked=True,
        color=['#2ecc71', '#8B4513', '#bdc3c7'], # Green, Brown, Grey
        ax=ax,
        width=0.4
    )
    
    # Annotations
    bowen_eff = (green_time / occupied_time) * 100
    utilization = (occupied_time / total_capacity) * 100
    
    plt.title(f'The Utilization Paradox (Run {run_id})\nBowen Efficiency: {bowen_eff:.1f}% | Utilization: {utilization:.1f}%', pad=20)
    plt.ylabel('Minutes')
    plt.xlabel('')
    plt.xticks([]) # Hide x axis label
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1))
    
    # Label Segments
    for c in ax.containers:
        ax.bar_label(c, label_type='center', fmt='%.0f m', color='white', weight='bold')
    
    plt.tight_layout()
    os.makedirs('results/plots', exist_ok=True)
    plt.savefig('results/plots/utilization_paradox.png')
    print("Saved results/plots/utilization_paradox.png")
    plt.close()

def plot_zonewise_validation():
    """
    Validation against Tatlock Source 9.
    3 Separate Box Plots (Subplots) to show distinct distributions clearly.
    """
    print("Generating Zonewise Validation Plot (Detailed)...")
    
    df = pd.read_csv('results/patient_performance.csv')
    
    # Tatlock Baselines
    baselines = {
        'Registration': 3.18,
        'Prep': 14.0, # Updated to 14m (Composite: Change + Prep)
        'Scanning': 35.0
    }
    
    # Calculate Composite Metric [Source 9 Definition]
    df['Zone 2 Prep'] = df['change_time'] + df['prep_time']
    
    # Mapping CSV columns to Display Names
    stage_map = {
        'reg_time': 'Registration',
        'Zone 2 Prep': 'Prep',
        'scan_time': 'Scanning'
    }
    
    colors = {'Registration': '#3498db', 'Prep': '#f1c40f', 'Scanning': '#2ecc71'}
    
    for col, stage_name in stage_map.items():
        plt.figure(figsize=(8, 8))
        
        # Filter Data
        data = df[col]
        
        # Plot Box
        sns.boxplot(y=data, color=colors[stage_name], width=0.4, showfliers=False)
        
        # Plot Strip (Raw Data Points)
        sns.stripplot(y=data, color=".2", alpha=0.3, size=4, jitter=True)
        
        # Plot Baseline
        baseline = baselines[stage_name]
        plt.axhline(baseline, color='red', linestyle='--', linewidth=2, label=f'Baseline {baseline}m')
        
        # Formatting
        plt.title(f"{stage_name} Distribution Comparison", fontsize=16, fontweight='bold')
        plt.ylabel('Minutes (Log Scale)' if stage_name == 'Scanning' else 'Minutes')
        plt.legend()
        
        # Apply visual polish
        sns.despine(trim=True)
        
        plt.tight_layout()
        filename = f"results/plots/validation_{stage_name.lower()}.png"
        plt.savefig(filename)
        print(f"Saved {filename}")
        plt.close()

def plot_icenter_gantt(run_id=0):
    """
    Source 111: iCenter Gantt Chart style.
    Visualizes magnet activity timeline.
    """
    print(f"Generating iCenter Gantt Chart for Run {run_id}...")
    
    df = pd.read_csv('results/magnet_events.csv')
    df = df[df['RunID'] == run_id]
    
    if df.empty:
        print("No event data for Gantt chart.")
        return

    # Color Map
    colors = {
        'scan': '#2ecc71',     # Green
        'setup': '#8B4513',    # Brown
        'flip': '#A0522D',     # Brown lighter
        'handover': '#D2691E', # Brownish orange
        'exit': '#CD853F'      # Light brown
    }
    
    fig, ax = plt.subplots(figsize=(15, 4))
    
    # Iterate and plot bars
    for idx, row in df.iterrows():
        y = 0 if row['Magnet'] == '3T' else 1
        start = row['Start']
        dur = row['Duration']
        color = colors.get(row['Type'], 'grey')
        
        ax.barh(y, dur, left=start, height=0.6, color=color, edgecolor='white', linewidth=0.5)
        
    # Formatting
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['3T Magnet', '1.5T Magnet'])
    ax.set_xlabel('Shift Time (Minutes)')
    ax.set_title(f'Magnet Utilization Timeline (Run {run_id})\nSource 111 Style Replication')
    ax.set_xlim(0, 720)
    
    # grid
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig('results/plots/icenter_gantt.png')
    print("Saved results/plots/icenter_gantt.png")
    plt.close()

if __name__ == "__main__":
    plot_utilization_paradox()
    plot_zonewise_validation()
    plot_icenter_gantt()
