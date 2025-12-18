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

def execute_batch(sims=1000, epochs=1):
    """
    Run Monte Carlo simulation batch.
    
    Args:
        sims: Number of simulations per epoch.
        epochs: Number of epochs to run.
    """
    config.HEADLESS = True
    total_sims = sims * epochs
    print(f"\nStarting Batch Execution: {total_sims} total simulations ({epochs} epochs x {sims} runs)")
    print(f"Workers: {multiprocessing.cpu_count()}")
    
    all_results = []
    start_time = time.time()
    
    # Run Epochs
    for epoch in range(epochs):
        epoch_start = time.time()
        print(f"\n--- Epoch {epoch+1}/{epochs} ---")
        
        # Prepare seeds
        base_seed = int(time.time()) + (epoch * sims)
        tasks = [(base_seed + i, {'duration': config.DEFAULT_DURATION}) for i in range(sims)]
        
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
        
    print("="*60)
