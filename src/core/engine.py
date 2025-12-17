"""
Engine Module - Main Simulation Loop
=====================================
Orchestrates the integration of SimPy, PyGame, and Statistics modules.
"""

import simpy
from src.config import STAFF_COUNT, AGENT_POSITIONS, SIM_SPEED, FPS
from src.visuals.renderer import RenderEngine
from src.visuals.sprites import Staff
from src.analysis.tracker import SimStats
from src.analysis.reporter import generate_report, print_summary
from src.core.workflow import patient_generator

def run_simulation(duration_minutes=120, max_patients=10, output_dir='results'):
    """
    Run the MRI Digital Twin simulation.
    
    This is the main entry point that integrates:
    - SimPy (discrete-event simulation)
    - PyGame (real-time visualization)
    - Statistics tracking (data collection)
    
    Args:
        duration_minutes: Total simulation time in minutes
        max_patients: Maximum number of patients to simulate
        output_dir: Directory for output files
    
    Returns:
        dict: Simulation results including stats and file paths
    """
    print("=" * 60)
    print("MRI DIGITAL TWIN - Starting Simulation")
    print("=" * 60)
    print(f"Duration: {duration_minutes} minutes")
    print(f"Max Patients: {max_patients}")
    print(f"Time Scale: 1 sim minute = {SIM_SPEED} real seconds")
    print("=" * 60 + "\n")
    
    # ========== INITIALIZE COMPONENTS ==========
    
    # 1. SimPy Environment
    env = simpy.Environment()
    
    # 2. Rendering Engine (PyGame)
    renderer = RenderEngine(title="MRI Digital Twin - Modular Architecture")
    
    # 3. Statistics Tracker
    stats = SimStats()
    
    # 4. Create SimPy Resources
    resources = {
        'porter': simpy.Resource(env, capacity=STAFF_COUNT['porter']),
        'backup_techs': simpy.Resource(env, capacity=STAFF_COUNT['backup_tech']),
        'scan_techs': simpy.Resource(env, capacity=STAFF_COUNT['scan_tech']),
        'magnet': simpy.Resource(env, capacity=1),  # Only 1 patient can scan at a time
    }
    
    # 5. Create Staff Sprites
    staff_dict = {
        'porter': Staff('porter', *AGENT_POSITIONS['porter_home']),
        'backup': [
            Staff('backup', AGENT_POSITIONS['backup_staging'][0] + i*30, 
                  AGENT_POSITIONS['backup_staging'][1])
            for i in range(STAFF_COUNT['backup_tech'])
        ],
        'scan': [
            Staff('scan', *AGENT_POSITIONS['scan_staging_3t']),
            Staff('scan', *AGENT_POSITIONS['scan_staging_15t'])
        ][:STAFF_COUNT['scan_tech']]
    }
    
    # Add staff to renderer
    renderer.add_sprite(staff_dict['porter'])
    for tech in staff_dict['backup']:
        renderer.add_sprite(tech)
    for tech in staff_dict['scan']:
        renderer.add_sprite(tech)
    
    # ========== START SIMULATION ==========
    
    # Start patient generator
    env.process(patient_generator(env, staff_dict, resources, stats, renderer, max_patients))
    
    # ========== MAIN LOOP (The Bridge) ==========
    
    running = True
    target_sim_time = duration_minutes
    
    print("Starting simulation loop...")
    print("Close the window to end early.\n")
    
    while running and env.now < target_sim_time:
        # Prepare stats for display
        current_stats = {
            'Sim Time': int(env.now),
            'Patients': stats.patients_completed,
            'In System': stats.patients_in_system,
        }
        
        # Render frame (returns False if window closed)
        running = renderer.render_frame(current_stats)
        
        # Advance simulation time
        # Real time per frame: 1/FPS seconds
        # Sim time per frame: (1/FPS) / SIM_SPEED minutes
        delta_sim_time = (1.0 / FPS) / (SIM_SPEED * 60)
        
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
    results = run_simulation(duration_minutes=60, max_patients=5)
    print("\n✓ Simulation engine test complete")
