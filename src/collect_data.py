
import pandas as pd
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.engine import MRISimulation

def calculate_metrics(patient_logs, scenario_name, parallel_mode):
    df = pd.DataFrame(patient_logs)
    if df.empty:
        return 0, 0.0

    # Throughput: Count of patients with exit_time
    completed = df[df['exit_time'].notna()]
    throughput = len(completed)

    # Idle Time Calculation
    # Busy Duration calculation matches app.py logic
    def calc_busy(row):
        if not parallel_mode: # Serial
            if pd.notnull(row['prep_start']) and pd.notnull(row['exit_time']):
                return row['exit_time'] - row['prep_start']
        else: # Parallel
            if pd.notnull(row['scan_start']) and pd.notnull(row['exit_time']):
                    return row['exit_time'] - row['scan_start']
        return 0.0

    df['Busy_Duration'] = df.apply(calc_busy, axis=1)
    total_busy = df['Busy_Duration'].sum()
    total_time = 12 * 60
    util_pct = (total_busy / total_time) * 100
    idle_pct = 100 - util_pct
    
    return throughput, idle_pct

def run_scenarios():
    scenarios = [
        {
            "name": "1. Baseline (Bleed to Death)",
            "staff": 4,
            "bed_flip": 5.0,
            "parallel": False
        },
        {
            "name": "2. Structural Optimization (Staffing)",
            "staff": 6,
            "bed_flip": 5.0,
            "parallel": True
        },
        {
            "name": "3. Full Optimization (Pit Crew)",
            "staff": 6,
            "bed_flip": 1.0,
            "parallel": True
        }
    ]

    iterations = 20 # Run 20 times to get a stable average
    print(f"Running {iterations} iterations per scenario...\n")

    results_summary = []

    for sc in scenarios:
        t_sum = 0
        i_sum = 0
        
        for i in range(iterations):
            sim = MRISimulation(
                simulation_hours=12,
                parallel_mode=sc['parallel'],
                staff_count=sc['staff'],
                bed_flip_time=sc['bed_flip']
            )
            data = sim.run()
            t, i_pct = calculate_metrics(data['patient_logs'], sc['name'], sc['parallel'])
            t_sum += t
            i_sum += i_pct
            
        avg_t = t_sum / iterations
        avg_i = i_sum / iterations
        
        results_summary.append({
            "Scenario": sc['name'],
            "Avg Throughput": avg_t,
            "Avg Idle %": avg_i
        })

    print("-" * 60)
    print(f"{'Scenario':<40} | {'Throughput':<10} | {'Idle %':<10}")
    print("-" * 60)
    for res in results_summary:
        print(f"{res['Scenario']:<40} | {res['Avg Throughput']:<10.1f} | {res['Avg Idle %']:<10.1f}")
    print("-" * 60)

if __name__ == "__main__":
    run_scenarios()
