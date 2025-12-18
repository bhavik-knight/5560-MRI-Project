"""
Reporter Module - Performance Reporting & Data Export
=====================================================
Generates detailed statistical reports and CSV exports 
distinguishing between Value-Added (Scanning) and Non-Value-Added time.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

def print_summary(stats, total_sim_time):
    """Prints a quick summary matching the SimStats.get_summary_stats output."""
    summary = stats.get_summary_stats(total_sim_time)
    
    print("\n" + "-"*30)
    print("QUICK SUMMARY")
    print("-"*30)
    print(f"Throughput:           {summary['throughput']} patients")
    print(f"Magnet Busy (Value):  {summary['magnet_busy_pct']}%")
    print(f"Magnet Idle:          {summary['magnet_idle_pct']}%")
    print(f"Avg Wait Time:        {summary['avg_wait_time']} min")
    print("-"*30 + "\n")

def generate_report(stats, duration, output_dir='results', filename='mri_digital_twin'):
    """
    Generate comprehensive simulation report.
    1. Aggregates data from PatientMetrics and MagnetMetrics
    2. Calculates performance ratios (Utilization, Efficiency)
    3. Prints console summary
    4. Exports to CSV
    """
    
    # --- 1. Patient Data Analysis ---
    if not stats.finished_patients:
        print("No patients completed. Skipping report generation.")
        return {}

    patient_data = []
    for p in stats.finished_patients:
        row = {
            'Patient_ID': p.id,
            'Type': p.type,
            'Has_IV': p.has_iv,
            'Is_Difficult': p.is_difficult,
            'Total_Time_In_System': round(p.total_time_in_system, 2),
            **{f"Time_{k.capitalize()}": round(v, 2) for k, v in p.durations.items()}
        }
        patient_data.append(row)

    df_patients = pd.DataFrame(patient_data)
    
    # --- 2. Magnet Data Analysis ---
    magnet_report = []
    for m_id, m in stats.magnets.items():
        total_productive = m.total_scan_time
        total_overhead = m.total_setup_time + m.total_flip_time + m.total_exit_time
        total_occupied = total_productive + total_overhead
        
        # Calculate process efficiency
        efficiency = (total_productive / total_occupied * 100) if total_occupied > 0 else 0
        
        magnet_report.append({
            'Magnet_ID': m_id,
            'Patients_Served': m.patients_served,
            'Scan_Time_Green': round(m.total_scan_time, 2),
            'Setup_Time_Brown': round(m.total_setup_time, 2),
            'Flip_Time_Brown': round(m.total_flip_time, 2),
            'Exit_Time_Brown': round(m.total_exit_time, 2),
            'Efficiency_Pct': round(efficiency, 2)
        })
    df_magnets = pd.DataFrame(magnet_report)

    # --- 3. Save to CSV ---
    os.makedirs(output_dir, exist_ok=True)
    p_file = f"{output_dir}/{filename}_patient_performance.csv"
    m_file = f"{output_dir}/{filename}_magnet_performance.csv"
    
    df_patients.to_csv(p_file, index=False)
    df_magnets.to_csv(m_file, index=False)

    # --- 4. Print Summary Report to Console ---
    print("\n" + "="*60)
    print("MRI DIGITAL TWIN - COMPREHENSIVE PERFORMANCE REPORT")
    print("="*60)
    
    # THROUGHPUT
    print(f"\nTHROUGHPUT SUMMARY:")
    print(f"Total Arrivals:       {stats.patients_arrived}")
    print(f"Completed Patients:   {stats.patients_completed}")
    print(f"Late Arrivals (Closed): {stats.late_arrivals}")
    
    # PATIENT STAGE AVERAGES (Value Stream Mapping)
    print(f"\nSTAGE-BY-STAGE AVERAGES (Minutes):")
    cols_to_avg = [c for c in df_patients.columns if c.startswith('Time_')]
    for col in cols_to_avg:
        avg = df_patients[col].mean()
        max_val = df_patients[col].max()
        print(f"  {col.replace('Time_', '').ljust(15)}: Avg={avg:5.1f} | Max={max_val:5.1f}")
    
    # MAGNET PRODUCTIVITY (Green vs Brown Time)
    print(f"\nMAGNET PRODUCTIVITY (Value-Added Analysis):")
    for _, m in df_magnets.iterrows():
        print(f" Magnet {m['Magnet_ID']}:")
        print(f"  - Patients Served:  {m['Patients_Served']}")
        print(f"  - Scan Time (Green): {m['Scan_Time_Green']:.1f} mins")
        print(f"  - Overhead (Brown):  {(m['Setup_Time_Brown'] + m['Flip_Time_Brown'] + m['Exit_Time_Brown']):.1f} mins")
        print(f"  - Process Efficiency: {m['Efficiency_Pct']}% [The Bowen Metric]")
    
    # SYSTEM TOTALS
    system_avg = df_patients['Total_Time_In_System'].mean()
    system_max = df_patients['Total_Time_In_System'].max()
    print(f"\nOVERALL SYSTEM PERFORMANCE:")
    print(f"Avg Time in System:   {system_avg:.1f} minutes")
    print(f"Max Time in System:   {system_max:.1f} minutes")
    print("="*60)
    print(f"CSV data exported to '{output_dir}'")
    print("="*60 + "\n")
    
    return {
        'patients': p_file,
        'magnets': m_file
    }
