"""
Engine Module - Main Simulation Loop
=====================================
Orchestrates the integration of SimPy, PyGame, and Statistics modules.
"""

import simpy
import sys
import pygame
from src.config import (
    STAFF_COUNT, AGENT_POSITIONS, SIM_SPEED, FPS, 
    DEFAULT_DURATION, WARM_UP_DURATION,
    MAGNET_3T_LOC, MAGNET_15T_LOC
)
from src.visuals.renderer import RenderEngine
from src.visuals.sprites import Staff
from src.analysis.tracker import SimStats
from src.analysis.reporter import generate_report, print_summary
from src.core.workflow import patient_generator

def run_simulation(duration=None, output_dir='results', record=False, video_format='mp4'):
    """
    Run the MRI Digital Twin simulation using shift duration model.
    
    This is the main entry point that integrates:
    - SimPy (discrete-event simulation)
    - PyGame (real-time visualization)
    - Statistics tracking (data collection)
    
    Uses time-based termination (shift duration) instead of patient count.
    Includes warm-up period to remove empty-system bias.
    
    Args:
        duration: Total simulation time in minutes (default: 720 = 12 hours)
        output_dir: Directory for output files
        video_format: Video format ('mkv' or 'mp4')
        record: If True, records simulation to video file
    
    Returns:
        dict: Simulation results including stats and file paths
    """
    # Use default duration if not specified
    if duration is None:
        duration = DEFAULT_DURATION
    
    print("=" * 60)
    print("MRI DIGITAL TWIN - Starting Simulation")
    print("=" * 60)
    print(f"Shift Duration: {duration} minutes ({duration/60:.1f} hours)")
    print(f"Warm-Up Period: {WARM_UP_DURATION} minutes ({WARM_UP_DURATION/60:.1f} hours)")
    print(f"Data Collection: {duration - WARM_UP_DURATION} minutes")
    print(f"Time Scale: 1 sim minute = {SIM_SPEED} real seconds")
    if record:
        print(f"Video Recording: ENABLED (results/simulation_video.{video_format})")
    print("=" * 60 + "\n")
    
    # ========== INITIALIZE COMPONENTS ==========
    
    # 1. SimPy Environment
    env = simpy.Environment()
    
    # 2. Rendering Engine (PyGame)
    renderer = RenderEngine(title="MRI Digital Twin - Modular Architecture", 
                           record_video=record, 
                           video_format=video_format)
    
    # 3. Statistics Tracker
    stats = SimStats()
    # 4. Create SimPy Resources
    resources = {
        'porter': simpy.PriorityResource(env, capacity=STAFF_COUNT['porter']),
        'backup_techs': simpy.Resource(env, capacity=STAFF_COUNT['backup_tech']),
        'scan_techs': simpy.Resource(env, capacity=STAFF_COUNT['scan_tech']),
        'admin_ta': simpy.Resource(env, capacity=STAFF_COUNT['admin']),
        'magnet_pool': simpy.Store(env, capacity=2),
        'change_1': simpy.Resource(env, capacity=1),
        'change_2': simpy.Resource(env, capacity=1),
        'change_3': simpy.Resource(env, capacity=1),
        'washroom_1': simpy.Resource(env, capacity=1),
        'washroom_2': simpy.Resource(env, capacity=1),
        'holding_room': simpy.Resource(env, capacity=1),  # Room 311 for inpatients
    }

    # Populate magnet pool AND keep references for visual tracking
    magnet_configs = []
    
    # Magnet 1: 3T
    m3t = simpy.Resource(env, capacity=1)
    m3t.last_exam_type = None 
    m3t_config = {
        'id': '3T',
        'resource': m3t,
        'loc': MAGNET_3T_LOC,
        'name': 'magnet_3t',
        'staging': AGENT_POSITIONS['scan_staging_3t'],
        'visual_state': 'clean'
    }
    resources['magnet_pool'].put(m3t_config)
    magnet_configs.append(m3t_config)
    
    # Magnet 2: 1.5T
    m15t = simpy.Resource(env, capacity=1)
    m15t.last_exam_type = None
    m15t_config = {
        'id': '1.5T',
        'resource': m15t,
        'loc': MAGNET_15T_LOC,
        'name': 'magnet_15t',
        'staging': AGENT_POSITIONS['scan_staging_15t'],
        'visual_state': 'clean'
    }
    resources['magnet_pool'].put(m15t_config)
    magnet_configs.append(m15t_config)

    
    # 5. Create Staff Sprites
    staff_dict = {
        'porter': Staff('porter', *AGENT_POSITIONS['porter_home']),
        'backup': [
            Staff('backup', *AGENT_POSITIONS[f'prep_{i+1}_center'])
            for i in range(min(2, STAFF_COUNT['backup_tech']))
        ],
        'scan': [
            Staff('scan', *AGENT_POSITIONS['scan_staging_3t']),
            Staff('scan', *AGENT_POSITIONS['scan_staging_15t'])
        ][:STAFF_COUNT['scan_tech']],
        'admin': Staff('admin', *AGENT_POSITIONS['admin_home']),
    }
    
    # Add staff to renderer
    renderer.add_sprite(staff_dict['porter'])
    for tech in staff_dict['backup']:
        renderer.add_sprite(tech)
    for tech in staff_dict['scan']:
        renderer.add_sprite(tech)
    renderer.add_sprite(staff_dict['admin'])
    
    # ========== START SIMULATION ==========
    
    # Start patient generator (runs until duration)
    env.process(patient_generator(env, staff_dict, resources, stats, renderer, duration))
    
    # ========== MAIN LOOP (The Bridge) ==========
    
    running = True
    
    print("Starting simulation loop...")
    print("Close the window to end early.\n")

    # PHASE 1 & 2: Normal Shift (inc. Warm-up and Cooldown)
    while running and env.now < duration:
        # Prepare Room States
        room_visual_states = {}
        for cfg in magnet_configs:
            room_visual_states[cfg['name']] = cfg['visual_state']
            
        # Determine Status Label
        if env.now < WARM_UP_DURATION:
            status = "WARM UP"
        elif not stats.generator_active:
            status = "CLOSED (Flushing Queue)"
        else:
            status = "NORMAL SHIFT"
            
        # Prepare stats for display
        current_stats = {
            'Sim Time': int(env.now),
            'Patients': stats.patients_completed,
            'In System': stats.patients_in_system,
            'Status': status,
            'Est Clear': f"{stats.est_clearing_time:.0f}m"
        }
        
        # Render frame (returns False if window closed)
        running = renderer.render_frame(current_stats, room_visual_states)
        
        # Advance simulation time
        delta_sim_time = (1.0 / FPS) * (60 / SIM_SPEED) / 60  # sim minutes per frame
        
        try:
            env.run(until=env.now + delta_sim_time)
        except simpy.core.EmptySchedule:
            break

    # PHASE 3: Run-to-Clear Overtime
    # Continue until all patients exit the system
    if running and stats.patients_in_system > 0:
        print(f"\nShift ended at {env.now:.1f}m. Entering Overtime to clear {stats.patients_in_system} patients.")
        
        while running and stats.patients_in_system > 0:
            # Update Room States
            room_visual_states = {}
            for cfg in magnet_configs:
                room_visual_states[cfg['name']] = cfg['visual_state']
                
            current_stats = {
                'Sim Time': int(env.now),
                'Patients': stats.patients_completed,
                'In System': stats.patients_in_system,
                'Status': 'OVERTIME (Clearing)'
            }
            
            running = renderer.render_frame(current_stats, room_visual_states)
            delta_sim_time = (1.0 / FPS) * (60 / SIM_SPEED) / 60
            
            try:
                env.run(until=env.now + delta_sim_time)
            except simpy.core.EmptySchedule:
                break
                
        print(f"All patients cleared. Stopping simulation at {env.now:.1f}m.")
        running = False # Stop the engine loop explicitly
    
    
    # ========== CLEANUP AND REPORTING ==========
    
    actual_duration = env.now
    renderer.cleanup()
    pygame.quit() # Extra safety
    if running is False:
        # If we exited loop naturally, we can assume task done.
        pass
    
    print("\n" + "=" * 60)
    print("Simulation Complete")
    print("=" * 60)
    print(f"Simulated Time: {actual_duration:.1f} minutes")
    print(f"Patients Completed: {stats.patients_completed}")
    print("=" * 60 + "\n")
    
    # Print summary to console
    print_summary(stats, actual_duration)
    
    # Generate comprehensive report
    print("Generating reports...")
    report_files = generate_report(stats, actual_duration, output_dir, filename='mri_digital_twin')
    
    print("\nReports saved:")
    for report_type, filepath in report_files.items():
        print(f"  {report_type}: {filepath}")
    
    # Return results
    return {
        'stats': stats,
        'duration': actual_duration,
        'utilization': stats.calculate_utilization(actual_duration),
        'files': report_files
    }

if __name__ == "__main__":
    # Quick test run
    results = run_simulation(duration=120)  # 2 hour test
    print("\n✓ Simulation engine test complete")
