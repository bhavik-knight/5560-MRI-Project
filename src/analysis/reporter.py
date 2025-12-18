"""
Reporter Module - Data Export and Reporting
============================================
Exports simulation statistics to CSV and generates summary reports.
"""

import csv
import os
from datetime import datetime

def export_to_csv(stats_object, output_dir='results', filename=None):
    """
    Export simulation statistics to CSV files.
    
    Args:
        stats_object: SimStats instance with collected data
        output_dir: Directory to save CSV files
        filename: Optional custom filename (without extension)
    
    Returns:
        dict: Paths to created files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = filename or f'simulation_{timestamp}'
    
    created_files = {}
    
    # 1. Export patient movement log
    movement_file = os.path.join(output_dir, f'{base_name}_movements.csv')
    with open(movement_file, 'w', newline='') as f:
        if stats_object.patient_log:
            writer = csv.DictWriter(f, fieldnames=stats_object.patient_log[0].keys())
            writer.writeheader()
            writer.writerows(stats_object.patient_log)
    created_files['movements'] = movement_file
    
    # 2. Export state changes log
    state_file = os.path.join(output_dir, f'{base_name}_states.csv')
    with open(state_file, 'w', newline='') as f:
        if stats_object.state_changes:
            writer = csv.DictWriter(f, fieldnames=stats_object.state_changes[0].keys())
            writer.writeheader()
            writer.writerows(stats_object.state_changes)
    created_files['states'] = state_file
    
    # 3. Export waiting room log
    waiting_file = os.path.join(output_dir, f'{base_name}_waiting_room.csv')
    with open(waiting_file, 'w', newline='') as f:
        if stats_object.waiting_room_log:
            writer = csv.DictWriter(f, fieldnames=stats_object.waiting_room_log[0].keys())
            writer.writeheader()
            writer.writerows(stats_object.waiting_room_log)
    created_files['waiting_room'] = waiting_file
    
    return created_files

def export_summary_stats(stats_object, total_sim_time, output_dir='results', filename=None):
    """
    Export summary statistics to CSV.
    
    Args:
        stats_object: SimStats instance
        total_sim_time: Total simulation duration in minutes
        output_dir: Directory to save CSV file
        filename: Optional custom filename
    
    Returns:
        str: Path to created summary file
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = filename or f'simulation_{timestamp}'
    summary_file = os.path.join(output_dir, f'{base_name}_summary.csv')
    
    # Get summary statistics
    summary = stats_object.get_summary_stats(total_sim_time)
    
    # Add simulation metadata
    summary['total_sim_time'] = total_sim_time
    summary['timestamp'] = timestamp
    
    # Write to CSV
    with open(summary_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=summary.keys())
        writer.writeheader()
        writer.writerow(summary)
    
    return summary_file

def generate_report(stats_object, total_sim_time, output_dir='results', filename=None):
    """
    Generate comprehensive report with all statistics.
    
    Args:
        stats_object: SimStats instance
        total_sim_time: Total simulation duration in minutes
        output_dir: Directory to save files
        filename: Optional base filename
    
    Returns:
        dict: Paths to all created files
    """
    # Export detailed logs
    log_files = export_to_csv(stats_object, output_dir, filename)
    
    # Export summary
    summary_file = export_summary_stats(stats_object, total_sim_time, output_dir, filename)
    
    # Generate text report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = filename or f'simulation_{timestamp}'
    report_file = os.path.join(output_dir, f'{base_name}_report.txt')
    
    summary = stats_object.get_summary_stats(total_sim_time)
    
    with open(report_file, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("MRI DIGITAL TWIN - SIMULATION REPORT\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"Simulation Duration: {total_sim_time} minutes\n")
        f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("-" * 60 + "\n")
        f.write("THROUGHPUT METRICS\n")
        f.write("-" * 60 + "\n")
        f.write(f"Total Arrivals:        {summary['total_arrivals']}\n")
        f.write(f"Completed Patients:    {summary['throughput']}\n")
        f.write(f"  - 3T Magnet Scans:   {summary['scans_3t']}\n")
        f.write(f"  - 1.5T Magnet Scans: {summary['scans_15t']}\n")
        f.write(f"Still in System:       {summary['patients_in_system']}\n\n")
        
        f.write("-" * 60 + "\n")
        f.write("MAGNET UTILIZATION (The Utilization Paradox)\n")
        f.write("-" * 60 + "\n")
        f.write(f"Busy Time (Value-Added):  {summary['magnet_busy_pct']}%\n")
        f.write(f"Occupied Time (Total):    {summary['magnet_occupied_pct']}%\n")
        f.write(f"Idle Time:                {summary['magnet_idle_pct']}%\n\n")
        
        f.write("NOTE: In Serial workflow, Occupied > Busy (prep happens in magnet)\n")
        f.write("      In Parallel workflow, Occupied ≈ Busy (prep happens elsewhere)\n\n")
        
        f.write("-" * 60 + "\n")
        f.write("WAITING ROOM BUFFER\n")
        f.write("-" * 60 + "\n")
        f.write(f"Average Wait Time:    {summary['avg_wait_time']} min\n")
        f.write(f"Maximum Wait Time:    {summary['max_wait_time']} min\n\n")
        
        f.write("-" * 60 + "\n")
        f.write("DATA LOGS\n")
        f.write("-" * 60 + "\n")
        f.write(f"Total Movements:      {summary['total_movements']}\n")
        f.write(f"Total State Changes:  {summary['total_state_changes']}\n\n")
        
        f.write("=" * 60 + "\n")
    
    return {
        **log_files,
        'summary': summary_file,
        'report': report_file
    }

def print_summary(stats_object, total_sim_time):
    """
    Print summary statistics to console.
    
    Args:
        stats_object: SimStats instance
        total_sim_time: Total simulation duration in minutes
    """
    summary = stats_object.get_summary_stats(total_sim_time)
    
    print("\n" + "=" * 60)
    print("SIMULATION SUMMARY")
    print("=" * 60)
    print(f"Duration: {total_sim_time} minutes")
    print(f"Throughput: {summary['throughput']} patients")
    print(f"  - 3T Magnet Scans:   {summary['scans_3t']}")
    print(f"  - 1.5T Magnet Scans: {summary['scans_15t']}")
    print(f"Magnet Busy (Value-Added): {summary['magnet_busy_pct']}%")
    print(f"Magnet Idle: {summary['magnet_idle_pct']}%")
    print(f"Avg Wait Time: {summary['avg_wait_time']} min")
    print("=" * 60 + "\n")
