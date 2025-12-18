"""
Engine Module - Main Simulation Loop
=====================================
Orchestrates the integration of SimPy, PyGame, and Statistics modules.
"""

import simpy
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
    }

    # Populate magnet pool
    resources['magnet_pool'].put({
        'id': '3T',
        'resource': simpy.Resource(env, capacity=1),
        'loc': MAGNET_3T_LOC,
        'name': 'magnet_3t',
        'staging': AGENT_POSITIONS['scan_staging_3t']
    })
    resources['magnet_pool'].put({
        'id': '1.5T',
        'resource': simpy.Resource(env, capacity=1),
        'loc': MAGNET_15T_LOC,
        'name': 'magnet_15t',
        'staging': AGENT_POSITIONS['scan_staging_15t']
    })

    
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
    
    while running and env.now < duration:
        # Prepare stats for display
        current_stats = {
            'Sim Time': int(env.now),
            'Patients': stats.patients_completed,
            'In System': stats.patients_in_system,
        }
        
        # Render frame (returns False if window closed)
        running = renderer.render_frame(current_stats)
        
        # Advance simulation time
        # Goal: Run simulation faster than real-time for quick results
        # SIM_SPEED = 0.5 means 1 sim minute takes 0.5 real seconds
        # So 1 real second = 2 sim minutes = 120 sim seconds
        # At 60 FPS: 1 frame = 1/60 sec = 2/60 sim minutes = 0.0333 sim minutes
        delta_sim_time = (1.0 / FPS) * (60 / SIM_SPEED) / 60  # sim minutes per frame
        
        try:
            env.run(until=env.now + delta_sim_time)
        except simpy.core.EmptySchedule:
            # No more events scheduled
            print("\nNo more events scheduled. Ending simulation.")
            break
    
    # ========== CLEANUP AND REPORTING ==========
    
    actual_duration = env.now
    renderer.cleanup()
    
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
