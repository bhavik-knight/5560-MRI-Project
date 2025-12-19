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
import src.config as config
from src.core.workflows.patient import run_generator as patient_generator
from src.core.staff_controller import StaffManager

def run_simulation(duration=None, output_dir='results', record=False, video_format='mp4', singles_line_mode=False, demand_multiplier=1.0, force_type=None, no_show_prob=None):
    """
    Run the MRI Digital Twin simulation using shift duration model.
    """
    # Use default duration if not specified
    if duration is None:
        duration = DEFAULT_DURATION
    
    # Create SimPy environment
    env = simpy.Environment()
    
    # Initialize Renderer
    if config.HEADLESS:
        renderer = type('MockRenderer', (), {'add_sprite': lambda *a: None, 'remove_sprite': lambda *a: None, 'cleanup': lambda *a: None, 'render_frame': lambda *a: True})()
    else:
        renderer = RenderEngine(title="MRI Digital Twin Simulation", record_video=record, video_format=video_format)

    # Initialize Stats Tracker
    stats = SimStats()

    # Define Resources
    # We use PriorityResource for critical shared assets to enable "pit crew" logic
    resources = {
        'porter': simpy.PriorityResource(env, capacity=STAFF_COUNT['porter']),
        'backup_techs': simpy.PriorityResource(env, capacity=STAFF_COUNT['backup_tech']),
        'scan_techs': simpy.Resource(env, capacity=STAFF_COUNT['scan_tech']),
        'admin_ta': simpy.Resource(env, capacity=STAFF_COUNT['admin']),
        'magnet_access': simpy.PriorityResource(env, capacity=2), # Controls access to magnet data
        'magnet_pool': simpy.Store(env, capacity=2), # Holds magnet objects
        
        # Room Resources (for seizing)
        'change_1': simpy.Resource(env, capacity=1),
        'change_2': simpy.Resource(env, capacity=1),
        'change_3': simpy.Resource(env, capacity=1),
        
        'prep_1': simpy.Resource(env, capacity=1),
        'prep_2': simpy.Resource(env, capacity=1),
        
        # New: Specific magnet resources for detailed tracking
        'magnet_3t_res': simpy.PriorityResource(env, capacity=1), 
        'magnet_15t_res': simpy.PriorityResource(env, capacity=1),
        
        # Mock waiting room buffers (just dictionaries for position tracking)
        'waiting_room_left': {},
        'waiting_room_right': {},
        
        # Global Flags
        'gap_mode_active': False
    }

    # Initialize Resource States
    # We track the last exam type to calculate sequence-dependent setup times (coil swaps)
    resources['magnet_3t_res'].last_exam_type = None
    resources['magnet_15t_res'].last_exam_type = None

    # Helper function for resource finding (simple round-robin or random can start here, 
    # but we will likely handle logic in patient workflow)
    resources['get_free_change_room'] = lambda: ('change_1') 

    # Populate Magnet Pool
    # We create magnet objects that carry their state and resource
    magnet_configs = [
        {'id': '3T', 'resource': resources['magnet_3t_res'], 'loc': MAGNET_3T_LOC, 'name': 'magnet_3t', 'visual_state': 'clean'},
        {'id': '1.5T', 'resource': resources['magnet_15t_res'], 'loc': MAGNET_15T_LOC, 'name': 'magnet_15t', 'visual_state': 'clean'}
    ]
    
    # Initialize magnet resources wrapper
    # We actually need to put these into the pool store
    for m in magnet_configs:
        resources['magnet_pool'].put(m)

    # Initialize Staff Agents
    # Note: Staff sprite does not need env/renderer/speed passed to init
    pos_porter = AGENT_POSITIONS['porter_home']
    pos_admin = AGENT_POSITIONS['admin_home']
    pos_backup = AGENT_POSITIONS['backup_staging'] # Corrected key
    
    # Split scan techs between magnets
    pos_scan_3t = AGENT_POSITIONS['scan_staging_3t']
    pos_scan_15t = AGENT_POSITIONS['scan_staging_15t']
    
    staff_dict = {
        'porter': Staff('porter', pos_porter[0], pos_porter[1]),
        'admin': Staff('admin', pos_admin[0], pos_admin[1]),
        'backup': [
            Staff('backup', pos_backup[0], pos_backup[1]),
            Staff('backup', pos_backup[0], pos_backup[1])
        ],
        'scan': [
            Staff('scan', pos_scan_3t[0], pos_scan_3t[1]),
            Staff('scan', pos_scan_15t[0], pos_scan_15t[1])
        ]
    }
    
    # Register staff sprites with renderer
    if renderer:
        renderer.add_sprite(staff_dict['porter'])
        renderer.add_sprite(staff_dict['admin'])
        for s in staff_dict['backup']: renderer.add_sprite(s)
        for s in staff_dict['scan']: renderer.add_sprite(s)
    
    # Start Staff Manager (Breaks, etc - though currently mainly visual)
    staff_mgr = StaffManager(env, staff_dict, resources)
    # staff_mgr.start() # If we add logic later

    # Start patient generator (runs until duration)
    env.process(patient_generator(env, staff_dict, resources, stats, renderer, duration, demand_multiplier=demand_multiplier, force_type=force_type, no_show_prob=no_show_prob))
    
    # Start Gap Monitor if enabled
    if singles_line_mode:
        env.process(monitor_gaps(env, resources))
    
    # ========== MAIN LOOP (The Bridge) ==========
    
    if config.HEADLESS:
        # High-Speed Batch execution
        env.run(until=duration)
        # Overtime clearing
        while stats.patients_in_system > 0:
            env.run(until=env.now + 1)
            if env.now > duration + 300: break # Safety exit
    else:
        # Interactive UI execution
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
    
    
    # ========== CLEANUP AND REPORTING ==========
    
    actual_duration = env.now
    renderer.cleanup()
    if not config.HEADLESS:
        pygame.quit() # Extra safety
        
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
    else:
        report_files = {} # Skip reporting internally for batch
    
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
