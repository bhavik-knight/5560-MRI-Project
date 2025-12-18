"""
Workflow Module - Patient Journey SimPy Process
================================================
Implements the swimlane workflow logic for patient flow through MRI department.
Includes dual-bay magnet routing with Poisson arrivals.
"""

import random
import simpy
import src.config as config
from src.config import (
    AGENT_POSITIONS, PROCESS_TIMES,
    MAGNET_3T_LOC, MAGNET_15T_LOC,
    PROB_IV_NEEDED, PROB_DIFFICULT_IV
)

def get_time(task):
    """Refined triangular sampling from config."""
    return random.triangular(*PROCESS_TIMES[task])

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
    5. Waiting Room (Buffer)
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
        porter.return_home()
    
    # ========== 3. CHANGING ==========
    patient.set_state('changing')
    stats.log_state_change(p_id, 'arriving', 'changing', env.now)
    
    change_time = get_time('change')
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
        
        # Move to tech's respective prep room
        prep_target = (tech.home_x, tech.home_y)
        
        patient.move_to(*prep_target)
        tech.move_to(*prep_target)
        
        while not patient.is_at_target():
            yield env.timeout(0.01)
        
        stats.log_movement(p_id, 'prep_room', env.now)
        
        # IV Setup (Source 33: 33% Probability)
        if random.random() < PROB_IV_NEEDED:
            if random.random() < PROB_DIFFICULT_IV:
                iv_time = get_time('iv_difficult')
            else:
                iv_time = get_time('iv_setup')
            yield env.timeout(iv_time)
        
        # Screening time
        screen_time = get_time('screening')
        yield env.timeout(screen_time)
        
        patient.set_state('prepped')
        stats.log_state_change(p_id, 'changing', 'prepped', env.now)
        
        tech.busy = False
        tech.return_home()
    
    # ========== 5. WAITING ROOM (The Critical Buffer) ==========
    patient.move_to(*AGENT_POSITIONS['waiting_room_center'])
    
    while not patient.is_at_target():
        yield env.timeout(0.01)
    
    stats.log_movement(p_id, 'waiting_room', env.now)
    stats.log_waiting_room(p_id, env.now, 'enter')
    
    # ========== 6. SCANNING (Load Balancing Routing) ==========
    # Select magnet with shortest queue
    if len(resources['magnet_3t'].queue) <= len(resources['magnet_15t'].queue):
        magnet_id = '3T'
        resource_key = 'magnet_3t'
        magnet_loc = MAGNET_3T_LOC
        magnet_name = 'magnet_3t'
        staging_pos = AGENT_POSITIONS['scan_staging_3t']
    else:
        magnet_id = '1.5T'
        resource_key = 'magnet_15t'
        magnet_loc = MAGNET_15T_LOC
        magnet_name = 'magnet_15t'
        staging_pos = AGENT_POSITIONS['scan_staging_15t']

    with resources[resource_key].request() as req:
        yield req
        
        stats.log_waiting_room(p_id, env.now, 'exit')
        
        # 6a. Escort patient to magnet (using Backup Tech)
        with resources['backup_techs'].request() as b_req:
            yield b_req
            backup_tech = next((t for t in staff_dict['backup'] if not t.busy), staff_dict['backup'][0])
            backup_tech.busy = True
            
            # Move to patient in waiting room
            backup_tech.move_to(patient.x, patient.y)
            while not backup_tech.is_at_target():
                yield env.timeout(0.01)
                
            # Escort to magnet room
            patient.move_to(*magnet_loc)
            backup_tech.move_to(*magnet_loc)
            while not patient.is_at_target():
                yield env.timeout(0.01)
            
            # Tech returns to prep room
            backup_tech.busy = False
            backup_tech.return_home()

        # 6b. Perform scanning (Scan Tech at terminal)
        scan_tech_3t = staff_dict['scan'][0]
        scan_tech_15t = staff_dict['scan'][1] if len(staff_dict['scan']) > 1 else scan_tech_3t
        
        # Assign tech based on chosen magnet
        scan_tech = scan_tech_3t if magnet_id == '3T' else scan_tech_15t
        scan_tech.busy = True
        
        patient.set_state('scanning')
        stats.log_state_change(p_id, 'prepped', 'scanning', env.now)
        stats.log_movement(p_id, magnet_name, env.now)
        
        # Step 1: Phased Setup (Hidden Time - Patient on table, room occupied but not scanning)
        stats.log_magnet_start(env.now, is_scanning=False)
        yield env.timeout(get_time('scan_setup'))
        stats.log_magnet_end(env.now)
        
        # Step 2: Phased Scanning (Active Value-Added Time)
        stats.log_magnet_start(env.now, is_scanning=True)
        scan_time = get_time('scan_duration')
        yield env.timeout(scan_time)
        stats.log_magnet_end(env.now)
        
        # Step 3: Phased Exit (Patient getting off table, room blocked)
        stats.log_magnet_start(env.now, is_scanning=False)
        yield env.timeout(get_time('scan_exit'))
        stats.log_magnet_end(env.now)
        
        # Step 4: Phased Bed Flip (Room cleared, prepping for next)
        stats.log_magnet_start(env.now, is_scanning=False)
        flip_time = get_time('bed_flip')
        yield env.timeout(flip_time)
        stats.log_magnet_end(env.now)

        scan_tech.busy = False
        # Scan tech remains at staging_pos (console)
    
    # ========== 7. EXIT ==========
    patient.move_to(*AGENT_POSITIONS['exit'])
    
    while not patient.is_at_target():
        yield env.timeout(0.01)
    
    stats.log_state_change(p_id, 'scanning', 'exited', env.now)
    stats.log_movement(p_id, 'exit', env.now)
    stats.log_completion(p_id, magnet_id)
    
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
