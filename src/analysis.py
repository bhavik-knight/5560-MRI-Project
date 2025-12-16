
import pandas as pd
import plotly.express as px
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.engine import MRISimulation

def run_experiment(hours=12, iterations=10, output_dir='results'):
    """
    Runs the simulation for both Serial and Parallel scenarios multiple times.
    Aggregates results and generates artifacts.
    """
    all_logs = []
    
    print(f"Starting Experiment: {hours} hours, {iterations} iterations.")
    
    scenarios = ['Serial', 'Parallel'] 
    # Mapped by boolean parallel_mode: False -> Serial, True -> Parallel
    
    for iteration in range(iterations):
        for scenario_name in scenarios:
            is_parallel = (scenario_name == 'Parallel')
            
            sim = MRISimulation(simulation_hours=hours, parallel_mode=is_parallel)
            results = sim.run()
            logs = results['patient_logs']
            
            # Enrich logs with iteration info
            for record in logs:
                record['Iteration'] = iteration
                record['Expected_Scenario'] = scenario_name # Redundant but explicit
                all_logs.append(record)
                
    df = pd.DataFrame(all_logs)
    
    if df.empty:
        print("No patients processed. Check simulation config.")
        return

    # --- METRICS CALCULATION ---
    # 1. Throughput (Patients per run)
    throughput = df.groupby(['Expected_Scenario', 'Iteration']).size().reset_index(name='Patient_Count')
    avg_throughput = throughput.groupby('Expected_Scenario')['Patient_Count'].mean().reset_index()
    
    # 2. Magnet Idle Time
    # Logic: 
    # Serial: Magnet is BUSY from prep_start to exit_time.
    # Parallel: Magnet is BUSY from scan_start to exit_time.
    # Idle Time = Total Time - Busy Time.
    
    # We need to calculate "Busy Duration" per patient per run.
    # Serial Busy = exit_time - prep_start
    # Parallel Busy = exit_time - scan_start
    
    def calc_busy(row):
        if row['Expected_Scenario'] == 'Serial':
            if row['prep_start'] is not None and row['exit_time'] is not None:
                return row['exit_time'] - row['prep_start']
        else:
            if row['scan_start'] is not None and row['exit_time'] is not None:
                return row['exit_time'] - row['scan_start']
        return 0.0

    df['Magnet_Busy_Duration'] = df.apply(calc_busy, axis=1)
    
    # Sum busy time per run
    magnet_busy = df.groupby(['Expected_Scenario', 'Iteration'])['Magnet_Busy_Duration'].sum().reset_index(name='Total_Busy_Time')
    
    # Total Simulation Time
    total_time_min = hours * 60
    magnet_busy['Idle_Time_Min'] = total_time_min - magnet_busy['Total_Busy_Time']
    magnet_busy['Idle_Pct'] = (magnet_busy['Idle_Time_Min'] / total_time_min) * 100
    
    avg_idle = magnet_busy.groupby('Expected_Scenario')['Idle_Pct'].mean().reset_index()
    
    # Print Summary
    print("\n--- Simulation Results ---")
    print("Average Throughput (Patients per 12h shift):")
    print(avg_throughput)
    print("\nAverage Magnet Idle Time (%):")
    print(avg_idle)
    
    # Export Stats
    os.makedirs(output_dir, exist_ok=True)
    stats_file = os.path.join(output_dir, 'simulation_stats.csv')
    throughput.merge(magnet_busy, on=['Expected_Scenario', 'Iteration']).to_csv(stats_file, index=False)
    print(f"\nStats collected to {stats_file}")

    # --- GANTT CHART (Visuals) ---
    # Generate Gantt for the *last* iteration of both scenarios.
    last_iter_df = df[df['Iteration'] == (iterations - 1)].copy()
    
    # Transform to Gantt format: Start, Finish, Resource (Magnet), Task (Prep, Scan)
    gantt_rows = []
    
    for _, row in last_iter_df.iterrows():
        scenario = row['Expected_Scenario']
        
        # Prep Block
        if row['prep_start'] is not None and row['scan_start'] is not None:
            # Only relevant for magnet utilization if SERIAL
            if scenario == 'Serial':
                gantt_rows.append({
                    'Scenario': scenario,
                    'Start': row['prep_start'],
                    'Finish': row['scan_start'],
                    'Task': 'Prep (Idle)',
                    'Patient': f"P{row['p_id']}"
                })
        
        # Scan Block (Scan + Flip)
        if row['scan_start'] is not None and row['exit_time'] is not None:
            gantt_rows.append({
                'Scenario': scenario,
                'Start': row['scan_start'],
                'Finish': row['exit_time'],
                'Task': 'Scan + Flip',
                'Patient': f"P{row['p_id']}"
            })

    if gantt_rows:
        df_gantt = pd.DataFrame(gantt_rows)
        # Convert minutes to datetime for Plotly Timeline (fake date)
        base_date = pd.Timestamp("2025-01-01 07:00")
        df_gantt['Start_Time'] = base_date + pd.to_timedelta(df_gantt['Start'], unit='m')
        df_gantt['Finish_Time'] = base_date + pd.to_timedelta(df_gantt['Finish'], unit='m')
        
        fig = px.timeline(
            df_gantt, 
            x_start="Start_Time", 
            x_end="Finish_Time", 
            y="Scenario", 
            color="Task",
            hover_data=['Patient'],
            title=f"Magnet Usage Gantt Chart (Last Iteration, {hours}h)",
            color_discrete_map={'Prep (Idle)': 'red', 'Scan + Flip': 'green'}
        )
        fig.update_yaxes(autorange="reversed")
        
        plot_file = os.path.join(output_dir, 'magnet_usage_gantt.html')
        fig.write_html(plot_file)
        print(f"Gantt chart saved to {plot_file}")

if __name__ == "__main__":
    run_experiment()
