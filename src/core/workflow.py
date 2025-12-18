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
    PROB_IV_NEEDED, PROB_DIFFICULT_IV,
    ROOM_COORDINATES, PROB_WASHROOM_USAGE
)

class PositionManager:
    """Manages available slots in waiting areas to prevent overlapping."""
    def __init__(self):
        # Dictionary to track occupied slots in each area/sub-area
        # Key: Area name, Value: List of (id, x, y)
        self.occupancy = {
            'zone1': {},
            'waiting_room_left': {},
            'waiting_room_right': {}
        }
        
    def get_grid_pos(self, area, p_id):
        """Calculate next available grid position for an area."""
        # Determine base room key
        if area.startswith('waiting_room'):
            room_key = 'waiting_room'
        else:
            room_key = area.split('_')[0]
            
        # Grid parameters
        start_x, start_y, width, height = ROOM_COORDINATES[room_key]
        
        # Override specific area boundaries based on user request
        if area == 'zone1':
            # Public room - left border
            base_x = start_x + 20
            base_y = start_y + 20
            max_y = start_y + height - 20
            spacing = 25
        elif area == 'waiting_room_left':
            # Waiting room - changed patients - left border
            base_x = start_x + 20
            base_y = start_y + 20
            max_y = start_y + height - 20
            spacing = 25
        elif area == 'waiting_room_right':
            # Waiting room - prepped patients - right border
            base_x = start_x + width - 20
            base_y = start_y + 20
            max_y = start_y + height - 20
            spacing = 25
            
        # Find first empty slot index
        occupied_indices = sorted(self.occupancy[area].keys())
        slot_idx = 0
        while slot_idx in occupied_indices:
            slot_idx += 1
            
        # Calculate x, y based on vertical-first grid
        column_capacity = max(1, (max_y - base_y) // spacing)
        col = slot_idx // column_capacity
        row = slot_idx % column_capacity
        
        if area == 'waiting_room_right':
            # Fill right-to-left
            x = base_x - (col * spacing)
        else:
            # Fill left-to-right
            x = base_x + (col * spacing)
            
        y = base_y + (row * spacing)
        
        # Save occupancy
        self.occupancy[area][slot_idx] = p_id
        return (x, y), slot_idx

    def release_pos(self, area, slot_idx):
        """Release a slot."""
        if slot_idx in self.occupancy[area]:
            self.occupancy[area].pop(slot_idx)

# Global position manager instance
pos_manager = PositionManager()

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

def patient_exit_process(env, patient, renderer, stats, p_id, magnet_id):
    """
    Separate process for patient exit journey (Change back -> Exit).
    Allows magnet bed flip to proceed in parallel.
    """
    # 7. Post-Scan Change (Back to Street Clothes)
    change_rooms = ['change_1_center', 'change_2_center', 'change_3_center']
    change_target = AGENT_POSITIONS[random.choice(change_rooms)]
    
    patient.set_state('changing') # Turn Blue again
    stats.log_state_change(p_id, 'scanning', 'changing', env.now)
    patient.move_to(*change_target)
    
    # Wait for movement to change room
    while not patient.is_at_target():
        yield env.timeout(0.01)
        
    stats.log_movement(p_id, 'change_room_exit', env.now)
    yield env.timeout(get_time('change_back'))
    
    # Now Exit Building
    patient.set_state('exited')
    stats.log_state_change(p_id, 'changing', 'exited', env.now)
    
    patient.move_to(*AGENT_POSITIONS['exit'])
    while not patient.is_at_target():
        yield env.timeout(0.01)
        
    renderer.remove_sprite(patient)
    stats.log_movement(p_id, 'exit', env.now)
    stats.log_completion(p_id, magnet_id)

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
    # Use grid position for Zone 1
    arrival_pos, arrival_slot = pos_manager.get_grid_pos('zone1', p_id)
    patient.move_to(*arrival_pos)
    stats.log_state_change(p_id, None, 'arriving', env.now)
    stats.log_movement(p_id, 'zone1', env.now)
    
    yield env.timeout(1)  # Brief arrival pause
    
    # ========== 2. TRANSPORT TO CHANGE ROOM (Porter) ==========
    with resources['porter'].request(priority=1) as req: # Lower priority than flips
        yield req
        
        # Porter moves to patient
        porter = staff_dict['porter']
        porter.busy = True
        porter.move_to(patient.x, patient.y)
        
        # Release Zone 1 position once porter arrives
        pos_manager.release_pos('zone1', arrival_slot)
        
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
    
    # ========== 4. PREP (Backup Tech Localization) ==========
    # Patient moves themselves from Change Room to Waiting Room first
    # Position: Left border of Waiting Room
    wr_left_pos, wr_left_slot = pos_manager.get_grid_pos('waiting_room_left', p_id)
    patient.move_to(*wr_left_pos)
    while not patient.is_at_target():
        yield env.timeout(0.01)
    
    stats.log_movement(p_id, 'waiting_room', env.now)
    stats.log_waiting_room(p_id, env.now, 'enter')

    # Now request Backup Tech to escort to prep room
    with resources['backup_techs'].request() as req:
        yield req
        stats.log_waiting_room(p_id, env.now, 'exit')
        
        # Find available backup tech (Load Balancing: Least Recently Used)
        free_techs = [t for t in staff_dict['backup'] if not t.busy]
        # Sort by last_used_time (default 0 if not set)
        tech = sorted(free_techs, key=lambda t: getattr(t, 'last_used_time', 0))[0]
        
        tech.busy = True
        tech.last_used_time = env.now
        
        # Tech meets patient in waiting room
        tech.move_to(patient.x, patient.y)
        while not tech.is_at_target():
            yield env.timeout(0.01)
        
        # Release waiting room left slot
        pos_manager.release_pos('waiting_room_left', wr_left_slot)
        
        # Move together to tech's respective prep room
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
        
        # RETURN to Waiting Room (Pit Crew Buffer)
        # Position: Right border of Waiting Room
        wr_right_pos, wr_right_slot = pos_manager.get_grid_pos('waiting_room_right', p_id)
        patient.move_to(*wr_right_pos)
        tech.move_to(*wr_right_pos)
        while not patient.is_at_target():
            yield env.timeout(0.01)
            
        stats.log_movement(p_id, 'waiting_room', env.now)
        stats.log_waiting_room(p_id, env.now, 'enter')
        
        # Tech returns home (localized to Zone 2)
        tech.busy = False
        tech.return_home()
        
        # Chance for WASHROOM break (Random occurrence while waiting)
        if random.random() < PROB_WASHROOM_USAGE:
            # Move to random washroom (1 or 2)
            washrooms = ['washroom_1', 'washroom_2']
            washroom_target = ROOM_COORDINATES[random.choice(washrooms)] # Using room rect for general location or center logic?
            # Actually, AGENT_POSITIONS has keys like 'prep_1_center', but no 'washroom_1_center'.
            # Layout.py draws rooms. ROOM_COORDINATES gives RECT. 
            # Let's approximate center from RECT since AGENT_POSITIONS doesn't list washrooms.
            # Wait, config had AGENT_POSITIONS for prep_1_center.
            # I should use rect center for washroom.
            w_choice = random.choice(washrooms)
            wx, wy, ww, wh = ROOM_COORDINATES[w_choice]
            washroom_pos = (wx + ww//2, wy + wh//2)
            
            # Release waiting room slot temporarily? 
            # Realistically, they keep their 'spot' or 'chart' in queue.
            # But visually, they leave the slot. 
            # Let's RELEASE the slot and RE-ACQUIRE when coming back to avoid ghosting.
            pos_manager.release_pos('waiting_room_right', wr_right_slot)
            
            patient.move_to(*washroom_pos)
            while not patient.is_at_target():
                yield env.timeout(0.01)
                
            stats.log_movement(p_id, 'washroom', env.now)
            yield env.timeout(get_time('washroom'))
            
            # Return to Waiting Room (Re-acquire slot)
            wr_right_pos, wr_right_slot = pos_manager.get_grid_pos('waiting_room_right', p_id)
            patient.move_to(*wr_right_pos)
            while not patient.is_at_target():
                yield env.timeout(0.01)
            stats.log_movement(p_id, 'waiting_room', env.now)
    
    # ========== 5. WAITING FOR MAGNET (Autonomous Signage) ==========
    # Patient is already in waiting room, wait for magnet availability
    
    # ========== 6. SCANNING (First Available Load Balancing) ==========
    # Wait for ANY available magnet from the pool
    magnet_config = yield resources['magnet_pool'].get()
    
    magnet_id = magnet_config['id']
    magnet_loc = magnet_config['loc']
    magnet_name = magnet_config['name']
    staging_pos = magnet_config['staging']
        
    stats.log_waiting_room(p_id, env.now, 'exit')
    
    # Release waiting room right position
    pos_manager.release_pos('waiting_room_right', wr_right_slot)
    
    # 6a. Patient moves AUTONOMOUSLY to magnet room (reading the digital sign)
    patient.move_to(*magnet_loc)
    while not patient.is_at_target():
        yield env.timeout(0.01)

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
    # Request Porter IMMEDIATELY so they can start moving/queuing while patient exits
    porter_req = resources['porter'].request(priority=0)
    
    stats.log_magnet_start(env.now, is_scanning=False)
    yield env.timeout(get_time('scan_exit'))
    stats.log_magnet_end(env.now)
    
    # PATIENT EXITS (Releases room, but room is still busy for flip)
    
    # PATIENT EXITS (Releases room, but room is still busy for flip)
    # Fork patient journey (Exit & Change) so Magnet/Porter can cycle immediately
    env.process(patient_exit_process(env, patient, renderer, stats, p_id, magnet_id))

    # Step 4: Phased Bed Flip (PORTER Fix - Porter must arrive to flip)
    yield porter_req
    try:
        stats.log_magnet_start(env.now, is_scanning=False)
        
        porter = staff_dict['porter']
        porter.busy = True
        
        # Porter moves to magnet to perform flip
        porter.move_to(*magnet_loc)
        while not porter.is_at_target():
            yield env.timeout(0.01)
            
        flip_time = get_time('bed_flip')
        yield env.timeout(flip_time)
        stats.log_magnet_end(env.now)
        
        porter.busy = False
        porter.return_home()
    finally:
        resources['porter'].release(porter_req)

    scan_tech.busy = False
    
    # Release magnet back to pool
    yield resources['magnet_pool'].put(magnet_config)

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
