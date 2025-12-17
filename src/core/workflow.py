"""
Workflow Module - Patient Journey SimPy Process
================================================
Implements the swimlane workflow logic for patient flow through MRI department.
Includes dual-bay magnet routing with Poisson arrivals.
"""

import random
import simpy
from src.config import (
    AGENT_POSITIONS, PROCESS_TIMES, PROBABILITIES,
    MAGNET_3T_LOC, MAGNET_15T_LOC
)

def triangular_sample(params):
    """
    Sample from triangular distribution.
    
    Args:
        params: Tuple of (min, mode, max) or single value
    
    Returns:
        float: Sampled value
    """
    if isinstance(params, (int, float)):
        return params
    return random.triangular(*params)

def poisson_sample(mean):
    """
    Sample from exponential distribution (Poisson process inter-arrival times).
    
    Args:
        mean: Mean inter-arrival time
    
    Returns:
        float: Sampled inter-arrival time
    """
    return random.expovariate(1.0 / mean)

def patient_journey(env, patient, staff_dict, resources, stats, renderer):
    """
    SimPy process defining a single patient's journey through the MRI suite.
    
    This implements the Swimlane workflow from Source 120:
    1. Arrival (Zone 1)
    2. Transport to Change Room (Porter)
    3. Changing
    4. Prep (Backup Tech)
    5. Gowned Waiting (Buffer)
    6. Scanning (Scan Tech + Magnet)
    7. Exit
    
    Args:
        env: SimPy environment
        patient: Patient sprite object
        staff_dict: Dict of staff agents {'porter': agent, 'backup': [agents], 'scan': [agents]}
        resources: Dict of SimPy resources
        stats: SimStats object for logging
        renderer: RenderEngine object
    """
    p_id = patient.p_id
    
    # ========== 1. ARRIVAL (Zone 1) ==========
    patient.set_state('arriving')
    patient.move_to(*AGENT_POSITIONS['zone1_center'])
    stats.log_state_change(p_id, None, 'arriving', env.now)
    stats.log_movement(p_id, 'zone1', env.now)
    
    yield env.timeout(1)  # Brief arrival pause
    
    # ========== 2. TRANSPORT TO CHANGE ROOM (Porter) ==========
    with resources['porter'].request() as req:
        yield req
        
        # Porter moves to patient
        porter = staff_dict['porter']
        porter.busy = True
        porter.move_to(patient.x, patient.y)
        
        # Wait for porter to arrive
        while not porter.is_at_target():
            yield env.timeout(0.01)
        
        # Select change room (random from 1-3)
        change_rooms = ['change_1_center', 'change_2_center', 'change_3_center']
        change_target = AGENT_POSITIONS[random.choice(change_rooms)]
        
        # Move together to change room
        patient.move_to(*change_target)
        porter.move_to(*change_target)
        
        while not patient.is_at_target():
            yield env.timeout(0.01)
        
        stats.log_movement(p_id, 'change_room', env.now)
        
        # Porter returns
        porter.busy = False
        porter.move_to(*AGENT_POSITIONS['porter_home'])
    
    # ========== 3. CHANGING ==========
    patient.set_state('changing')
    stats.log_state_change(p_id, 'arriving', 'changing', env.now)
    
    change_time = triangular_sample(PROCESS_TIMES['change'])
    yield env.timeout(change_time)
    
    # ========== 4. PREP (Backup Tech) ==========
    with resources['backup_techs'].request() as req:
        yield req
        
        # Find available backup tech
        tech = next((t for t in staff_dict['backup'] if not t.busy), staff_dict['backup'][0])
        tech.busy = True
        tech.move_to(patient.x, patient.y)
        
        while not tech.is_at_target():
            yield env.timeout(0.01)
        
        # Move to prep room
        prep_rooms = ['prep_1_center', 'prep_2_center']
        prep_target = AGENT_POSITIONS[random.choice(prep_rooms)]
        
        patient.move_to(*prep_target)
        tech.move_to(*prep_target)
        
        while not patient.is_at_target():
            yield env.timeout(0.01)
        
        stats.log_movement(p_id, 'prep_room', env.now)
        
        # IV Setup (if needed)
        if random.random() < PROBABILITIES['needs_iv']:
            if random.random() < PROBABILITIES['difficult_iv']:
                iv_time = triangular_sample(PROCESS_TIMES['iv_difficult'])
            else:
                iv_time = triangular_sample(PROCESS_TIMES['iv_setup'])
            yield env.timeout(iv_time)
        
        # Screening time
        screen_time = triangular_sample(PROCESS_TIMES['screening'])
        yield env.timeout(screen_time)
        
        patient.set_state('prepped')
        stats.log_state_change(p_id, 'changing', 'prepped', env.now)
        
        tech.busy = False
        tech.move_to(*AGENT_POSITIONS['backup_staging'])
    
    # ========== 5. GOWNED WAITING (The Critical Buffer) ==========
    patient.move_to(*AGENT_POSITIONS['gowned_waiting_center'])
    
    while not patient.is_at_target():
        yield env.timeout(0.01)
    
    stats.log_movement(p_id, 'gowned_waiting', env.now)
    stats.log_gowned_waiting(p_id, env.now, 'enter')
    
    # ========== 6. SCANNING (Dual-Bay Magnet Routing) ==========
    with resources['magnet'].request() as req:
        yield req
        
        stats.log_gowned_waiting(p_id, env.now, 'exit')
        
        # Determine which magnet to use (priority to 3T)
        # Check if 3T scan tech is available
        scan_tech_3t = staff_dict['scan'][0]  # First scan tech assigned to 3T
        scan_tech_15t = staff_dict['scan'][1] if len(staff_dict['scan']) > 1 else staff_dict['scan'][0]
        
        # Priority routing: prefer 3T, use 1.5T if 3T tech is busy
        if not scan_tech_3t.busy:
            # Use 3T magnet
            scan_tech = scan_tech_3t
            magnet_target = MAGNET_3T_LOC
            magnet_name = 'magnet_3t'
            staging_pos = AGENT_POSITIONS['scan_staging_3t']
        elif not scan_tech_15t.busy:
            # Use 1.5T magnet
            scan_tech = scan_tech_15t
            magnet_target = MAGNET_15T_LOC
            magnet_name = 'magnet_15t'
            staging_pos = AGENT_POSITIONS['scan_staging_15t']
        else:
            # Both busy, use whichever becomes available (default to 3T)
            scan_tech = scan_tech_3t
            magnet_target = MAGNET_3T_LOC
            magnet_name = 'magnet_3t'
            staging_pos = AGENT_POSITIONS['scan_staging_3t']
        
        scan_tech.busy = True
        
        # Move to selected magnet
        patient.move_to(*magnet_target)
        scan_tech.move_to(magnet_target[0] - 30, magnet_target[1])
        
        while not patient.is_at_target():
            yield env.timeout(0.01)
        
        patient.set_state('scanning')
        stats.log_state_change(p_id, 'prepped', 'scanning', env.now)
        stats.log_movement(p_id, magnet_name, env.now)
        stats.log_magnet_start(env.now, is_scanning=True)
        
        # Scan duration
        scan_time = triangular_sample(PROCESS_TIMES['scan'])
        yield env.timeout(scan_time)
        
        # Bed flip
        flip_time = PROCESS_TIMES['bed_flip_future']  # Using parallel workflow
        yield env.timeout(flip_time)
        
        stats.log_magnet_end(env.now)
        
        scan_tech.busy = False
        scan_tech.move_to(*staging_pos)
    
    # ========== 7. EXIT ==========
    patient.move_to(*AGENT_POSITIONS['exit'])
    
    while not patient.is_at_target():
        yield env.timeout(0.01)
    
    stats.log_state_change(p_id, 'scanning', 'exited', env.now)
    stats.log_movement(p_id, 'exit', env.now)
    
    # Remove patient from rendering
    renderer.remove_sprite(patient)

def patient_generator(env, staff_dict, resources, stats, renderer, duration):
    """
    Generate patients at scheduled intervals until shift ends.
    
    Args:
        env: SimPy environment
        staff_dict: Dict of staff agents
        resources: Dict of SimPy resources
        stats: SimStats object
        renderer: RenderEngine object
        duration: Simulation duration in minutes (patients arrive until this time)
    """
    from src.visuals.sprites import Patient
    
    p_id = 0
    while env.now < duration:
        p_id += 1
        
        # Create patient sprite
        patient = Patient(p_id, *AGENT_POSITIONS['zone1_center'])
        renderer.add_sprite(patient)
        
        # Start patient journey
        env.process(patient_journey(env, patient, staff_dict, resources, stats, renderer))
        
        # Wait for next patient (Poisson process - exponential inter-arrival)
        inter_arrival = poisson_sample(PROCESS_TIMES['mean_inter_arrival'])
        yield env.timeout(inter_arrival)
