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
    
    # ... (skipping lines for brevity) ...

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
