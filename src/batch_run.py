"""
Batch Execution Orchestrator
============================
Manages high-performance parallel execution of headless simulations.
"""

import multiprocessing
import pandas as pd
import numpy as np
import time
from src.core.headless import HeadlessSimulation
import src.config as config

def _worker_task(seed_and_settings):
    """Helper for multiprocessing pool."""
    seed, settings = seed_and_settings
    sim = HeadlessSimulation(settings, seed)
    return sim.run()

def execute_batch(sims=1000, epochs=1, singles_line_mode=False, demand_multiplier=1.0, force_type=None):
    """
    Run Monte Carlo simulation batch.
    
    Args:
        sims: Number of simulations per epoch.
        epochs: Number of epochs to run.
        singles_line_mode: Enable singles line logic.
        demand_multiplier: Scale patient arrival rate (1.0 = 100%).
        force_type: Force specific protocol (for block scheduling experiments).
    """
    config.HEADLESS = True
    total_sims = sims * epochs
    print(f"\nStarting Batch Execution: {total_sims} total simulations ({epochs} epochs x {sims} runs)")
    print(f"Workers: {multiprocessing.cpu_count()}")
    print(f"Mode: {'Singles Line' if singles_line_mode else 'Baseline'} | Demand: {demand_multiplier*100:.0f}% | Forced Type: {force_type if force_type else 'None'}")
    
    all_results = []
    start_time = time.time()
    
    # Run Epochs
    for epoch in range(epochs):
        epoch_start = time.time()
        print(f"\n--- Epoch {epoch+1}/{epochs} ---")
        
        # Prepare seeds
        base_seed = int(time.time()) + (epoch * sims)
        tasks = [(base_seed + i, {'duration': config.DEFAULT_DURATION, 
                                  'singles_line_mode': singles_line_mode,
                                  'demand_multiplier': demand_multiplier,
                                  'force_type': force_type}) for i in range(sims)]
        
        # Parallel Execution
        with multiprocessing.Pool() as pool:
            # Chunksize optimization could be done, but default is usually okay
            epoch_results = pool.map(_worker_task, tasks)
            all_results.extend(epoch_results)
            
        epoch_dur = time.time() - epoch_start
        print(f"Epoch completed in {epoch_dur:.2f}s ({sims/epoch_dur:.1f} sims/sec)")

    total_time = time.time() - start_time
    print(f"\nBatch Complete in {total_time:.2f}s")
    
    # Process Results
    process_results(all_results)

def process_results(results_list):
    """Aggregate and report stats."""
    df = pd.DataFrame(results_list)
    
    print("\n" + "="*60)
    print("MONTE CARLO SIMULATION REPORT")
    print("="*60)
    print(f"Total Runs: {len(df)}")
    
    # 1. Operational Metrics
    print("\n[ Operational Metrics ]")
    print(f"Throughput (Patients):    {df['patients_completed'].mean():.2f} ± {df['patients_completed'].std():.2f}")
    print(f"Patients In System (End): {df['patients_in_system'].mean():.2f}")
    print(f"Late Arrivals (Avg):      {df['late_arrivals'].mean():.2f}")
    print(f"No Shows (Avg):           {df['no_shows'].mean():.2f}")
    
    # 2. Resource Utilization
    # Create valid dataframe for occupied minutes
    occ_list = df['occupied_minutes'].tolist()
    occ_df = pd.DataFrame(occ_list)
    
    # Calculate Utilization %
    # Formula: (Occupied / (Duration * Capacity)) * 100
    duration = config.DEFAULT_DURATION
    
    caps = {
        'magnet_3t': 1,
        'magnet_15t': 1,
        'magnet_pool': 2, # if aggregated
        'prep_rooms': 2,
        'change_rooms': 3,
        'washrooms': 2,
        'waiting_room': 3, # Soft capacity but used for calc
        'room_311': 2
    }
    
    print("\n[ Resource Utilization % ]")
    keys_to_check = list(caps.keys())
    # Also Map internal keys if different
    
    for res_name, capacity in caps.items():
        if res_name in occ_df.columns:
            mean_occupied = occ_df[res_name].mean()
            util_pct = (mean_occupied / (duration * capacity)) * 100
            std_occupied = occ_df[res_name].std()
            std_pct = (std_occupied / (duration * capacity)) * 100
            print(f"{res_name.ljust(15)}: {util_pct:.1f}% ± {std_pct:.1f}%")

    # 2b. Magnet Idle Time %
    # Formula: (Idle_Minutes / Duration) * 100
    print("\n[ Magnet Idle Time % ]")
    if 'magnet_3t_idle' in df.columns:
         idle_3t = (df['magnet_3t_idle'].mean() / duration) * 100
         idle_3t_std = (df['magnet_3t_idle'].std() / duration) * 100
         print(f"Magnet 3T Idle : {idle_3t:.1f}% ± {idle_3t_std:.1f}%")
    if 'magnet_15t_idle' in df.columns:
         idle_15t = (df['magnet_15t_idle'].mean() / duration) * 100
         idle_15t_std = (df['magnet_15t_idle'].std() / duration) * 100
         print(f"Magnet 1.5T Idle: {idle_15t:.1f}% ± {idle_15t_std:.1f}%")

    # 2c. Overall Magnet Utilization
    if 'magnet_3t' in occ_df.columns and 'magnet_15t' in occ_df.columns:
        total_mag_cap = caps['magnet_3t'] + caps['magnet_15t']
        combined_occ = occ_df['magnet_3t'] + occ_df['magnet_15t']
        overall_util = (combined_occ.mean() / (duration * total_mag_cap)) * 100
        overall_std = (combined_occ.std() / (duration * total_mag_cap)) * 100
        print(f"Overall Magnet  : {overall_util:.1f}% ± {overall_std:.1f}%")

    # 3. Patient Wait Times
    print("\n[ Patient Experience (Avg Minutes) ]")
    
    # Collect all patient dicts
    # This might be memory intensive for 100k runs.
    # We'll calculate averages per run, then average of averages?
    # No, 'patient_data' is a dict of pid->data.
    # We want system-wide averages.
    # Let's aggregate summary stats PER RUN first to avoid huge DF?
    # But for now, direct list is robust.
    
    all_patients = []
    for p_map in df['patient_data']:
        all_patients.extend(p_map.values())
        
    if all_patients:
        # Optimization: If very large, process in chunks or use numpy
        p_df = pd.DataFrame(all_patients)
        
        print(f"Total Time:      {p_df['total_time'].mean():.1f} ± {p_df['total_time'].std():.1f} min")
        print(f"Registration:    {p_df['reg_time'].mean():.1f} min")
        print(f"Waiting:         {p_df['wait_time'].mean():.1f} min")
        print(f"Prep:            {p_df['prep_time'].mean():.1f} min")
        print(f"Scanning:        {p_df['scan_time'].mean():.1f} min")
        print(f"Inpatient Hold:  {p_df['holding_time'].mean():.1f} min")
    else:
        print("No patient data available.")
        
    # 4. Utilization Paradox & Bowen Metric
    print("\n[ Efficiency Analysis ]")
    
    # Aggregated Magnet Metrics
    total_scan_val = sum([r['magnet_metrics']['scan_value_added'] for r in df.to_dict('records')])
    total_scan_ovh = sum([r['magnet_metrics']['scan_overhead'] for r in df.to_dict('records')])
    
    # Paradox: Occupied vs Productive
    # Denominator: Total Magnet Capacity Minutes Available
    # (Sims * Duration * 2 magnets)
    total_mag_capacity = len(df) * duration * 2
    
    util_occupied = ((total_scan_val + total_scan_ovh) / total_mag_capacity) * 100
    util_productive = (total_scan_val / total_mag_capacity) * 100
    
    print(f"Utilization (Occupied):   {util_occupied:.1f}% (Green + Brown)")
    print(f"Utilization (Productive): {util_productive:.1f}% (Green Only)")
    print(f"Operational Overhead:     {(util_occupied - util_productive):.1f}%")

    # The Bowen Metric: Process Efficiency
    if (total_scan_val + total_scan_ovh) > 0:
        bowen_eff = (total_scan_val / (total_scan_val + total_scan_ovh)) * 100
        print(f"Bowen Efficiency:         {bowen_eff:.1f}% (Value-Added Ratio)")
    else:
        print("Bowen Efficiency:         N/A")
        
    # 5. Protocol Breakdown
    print("\n[ Protocol Mix ]")
    # Aggregate counts
    total_counts = {}
    for counts in df['scan_counts']:
        for proto, count in counts.items():
            total_counts[proto] = total_counts.get(proto, 0) + count
            
    # Normalize per sim run
    sim_count = len(df)
    sorted_protos = sorted(total_counts.items(), key=lambda x: x[1], reverse=True)
    
    for proto, total in sorted_protos:
        avg_per_run = total / sim_count
        prob_pct = (total / sum(total_counts.values())) * 100
        print(f"{proto.ljust(15)}: {avg_per_run:.1f} avg/run ({prob_pct:.1f}%)")

    print("="*60)
    
    # --- SAVE CSV DATA FOR DASHBOARD ---
    import os
    os.makedirs('results', exist_ok=True)
    
    # 1. Patient Performance (Detailed)
    patient_records = []
    for run_id, res in enumerate(results_list):
        p_data_map = res['patient_data']
        for p_id, p_metrics in p_data_map.items():
            rec = p_metrics.copy()
            rec['RunID'] = run_id
            rec['PatientID'] = p_id
            patient_records.append(rec)
            
    if patient_records:
        pd.DataFrame(patient_records).to_csv('results/patient_performance.csv', index=False)
        print(f"Saved results/patient_performance.csv ({len(patient_records)} records)")

    # 2. Magnet Events (Gantt)
    event_records = []
    for run_id, res in enumerate(results_list):
        if 'magnet_events' in res:
            for evt in res['magnet_events']:
                rec = evt.copy()
                rec['RunID'] = run_id
                event_records.append(rec)
                
    if event_records:
        pd.DataFrame(event_records).to_csv('results/magnet_events.csv', index=False)
        print(f"Saved results/magnet_events.csv ({len(event_records)} records)")
        
    # 3. Magnet Summary (Utilization Paradox)
    mag_summary = []
    for run_id, res in enumerate(results_list):
        if 'magnet_metrics' in res:
             metrics = res['magnet_metrics']
             mag_summary.append({
                 'RunID': run_id,
                 'Scan_Value_Added': metrics['scan_value_added'],
                 'Scan_Overhead': metrics['scan_overhead'],
                 'Scan_Gap': metrics['scan_gap']
             })
    
    if mag_summary:
        pd.DataFrame(mag_summary).to_csv('results/magnet_performance.csv', index=False)
        print(f"Saved results/magnet_performance.csv ({len(mag_summary)} records)")
