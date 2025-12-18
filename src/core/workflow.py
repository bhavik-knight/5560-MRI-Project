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
    ROOM_COORDINATES, PROB_WASHROOM_USAGE,
    PURPLE_REGISTERED, EXAM_TYPES
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
            base_x = 100
            base_y = start_y + 20
            max_y = start_y + height - 20
            spacing = 35
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

# Global Admin Queue for visual line formation
ADMIN_QUEUE = []

def update_admin_queue():
    """Update positions of all patients waiting for Admin."""
    base_x, base_y = AGENT_POSITIONS['admin_home']
    # Queue starts to the right of the desk (towards entrance)
    queue_start_x = base_x + 50 
    spacing = 30
    
    for i, patient in enumerate(ADMIN_QUEUE):
        target_x = queue_start_x + (i * spacing)
        patient.move_to(target_x, base_y)

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

def use_washroom(env, patient, resources, stats, return_pos):
    """
    Helper for probabilistic washroom usage.
    Seizes nearest washroom resource.
    """
    # Pick random washroom
    w_idx = random.choice([1, 2])
    w_name = f'washroom_{w_idx}'
    w_res = resources[w_name]
    
    # Calculate coords
    wx, wy, ww, wh = ROOM_COORDINATES[w_name]
    target = (wx + ww//2, wy + wh//2)
    
    with w_res.request() as req:
        yield req
        
        patient.move_to(*target)
        while not patient.is_at_target():
             yield env.timeout(0.01)
             
        stats.log_movement(patient.p_id, 'washroom', env.now)
        yield env.timeout(get_time('washroom'))
        
    # Return to previous spot
    patient.move_to(*return_pos)
    while not patient.is_at_target():
        yield env.timeout(0.01)

def patient_exit_process(env, patient, renderer, stats, p_id, magnet_id, resources):
    """
    Separate process for patient exit journey (Change back -> Exit).
    Allows magnet bed flip to proceed in parallel.
    """
    # 7. Post-Scan Change (Back to Street Clothes)
    # Move to Change Staging
    staging_loc = AGENT_POSITIONS['change_staging']
    patient.move_to(*staging_loc)
    while not patient.is_at_target(): yield env.timeout(0.01)
    
    # Seize Change Room (competing with incoming patients)
    selected_room = None
    selected_req = None
    change_room_keys = ['change_1', 'change_2', 'change_3']
    
    while selected_room is None:
        random.shuffle(change_room_keys)
        for key in change_room_keys:
             # Can pick any free one
            if resources[key].count < resources[key].capacity:
                selected_room = key
                selected_req = resources[key].request()
                break
        
        if selected_room:
             yield selected_req
        else:
             yield env.timeout(0.1)
             
    # Enter Room
    patient.set_state('changing') # Turn Blue again
    stats.log_state_change(p_id, 'scanning', 'changing', env.now)
    
    room_target = AGENT_POSITIONS[f"{selected_room}_center"]
    patient.move_to(*room_target)
    
    # Wait for movement to change room (Visual Logic)
    while not patient.is_at_target():
        yield env.timeout(0.01)
        
    stats.log_movement(p_id, 'change_room_exit', env.now)
    yield env.timeout(get_time('change_back'))
    
    # Release Room
    resources[selected_room].release(selected_req)
    
    # Now Exit Building - Visual Walk
    # Currently state is 'changing' (Blue) or should we make them 'exited' (Grey) while walking?
    # User request implies they should be counted as "in system" until they leave right side.
    
    # Let's keep them 'changing' (Blue) or 'walking_exit' until they vanish.
    # Or just keep logic: state change triggers counter decrement.
    
    # Move to Exit Target FIRST
    patient.move_to(*AGENT_POSITIONS['exit'])
    while not patient.is_at_target():
        yield env.timeout(0.01)
        
    # NOW decrement system counter
    patient.set_state('exited')
    stats.log_state_change(p_id, 'changing', 'exited', env.now)
    
    renderer.remove_sprite(patient)
    stats.log_movement(p_id, 'exit', env.now)
    stats.log_completion(p_id, magnet_id)

def patient_journey(env, patient, staff_dict, resources, stats, renderer):
    """
    Implements the "Pit Crew" workflow with conditional staff logic.
    Now includes branching for Inpatient (high acuity) vs Outpatient workflows.
    """
    from src.core.inpatient_workflow import inpatient_workflow
    
    p_id = patient.p_id
    
    # ========== Step 0: Patient Classification ==========
    is_inpatient = random.random() < config.PROB_INPATIENT
    patient.patient_type = 'inpatient' if is_inpatient else 'outpatient'
    
    if is_inpatient:
        patient.color = config.COLOR_INPATIENT  # Dark Pink
        # Inpatient path: bypass registration, go to holding room
        yield from inpatient_workflow(env, patient, staff_dict, resources, stats, renderer, p_id)
        return  # Exit after inpatient workflow completes
    else:
        patient.color = config.COLOR_OUTPATIENT  # Dodger Blue
    
    # ========== Step 1: Arrival & Gatekeeper Queue ==========
    patient.set_state('arriving')
    stats.log_state_change(p_id, None, 'arriving', env.now)
    
    # Action 1: Approach Desk / Queue Logic
    # Join visual queue immediately
    ADMIN_QUEUE.append(patient)
    update_admin_queue()
    
    # Wait for Admin Resource (Physically Queueing)
    with resources['admin_ta'].request() as req:
        # While waiting for req, patient is moving towards their queue slot
        yield req
        
        # ========== Step 2: Registration ==========
        # Resource seized. Leave visual queue logic.
        if patient in ADMIN_QUEUE:
            ADMIN_QUEUE.remove(patient)
            update_admin_queue()
            
        # Move to Admin Desk Interaction Point
        admin_x, admin_y = AGENT_POSITIONS['admin_home']
        patient.move_to(admin_x, admin_y + 25)
        
        # Wait until arrival at desk
        while not patient.is_at_target():
             yield env.timeout(0.01)

        # WAIT FOR ADMIN TA TO ARRIVE (Physical Presence Check)
        admin_sprite = staff_dict['admin'] # Get sprite reference
        while not admin_sprite.is_at_target(): # Assuming Admin is walking home
             # Or check distance to home strictly
             dist_admin = ((admin_sprite.x - admin_x)**2 + (admin_sprite.y - admin_y)**2)**0.5
             if dist_admin < 5: break
             yield env.timeout(0.01)
             
        # Now Registration Process
        patient.color = PURPLE_REGISTERED
        stats.log_state_change(p_id, 'arriving', 'registered', env.now)
        yield env.timeout(get_time('registration'))
        
        # ========== Step 3 & 4: Transport Decision (The TA Heuristic) ==========
        porter_res = resources['porter']
        
        # Select change room target
        change_rooms = ['change_1_center', 'change_2_center', 'change_3_center']
        change_target = AGENT_POSITIONS[random.choice(change_rooms)]
        
        if porter_res.count >= porter_res.capacity or len(porter_res.queue) > 0:
            # === Branch A: Porter Busy -> TA Escorts ===
            admin = staff_dict['admin']
            admin.busy = True
            
            # TA moves to patient
            admin.move_to(patient.x, patient.y)
            while not admin.is_at_target(): yield env.timeout(0.01)
                
            # TA Escorts to CHANGE STAGING (Zone 2 Hallway)
            # User Request: Treat Zone 2 as staging. Staff drops them off here.
            staging_loc = AGENT_POSITIONS['change_staging']
            patient.move_to(*staging_loc)
            admin.move_to(*staging_loc)
            while not patient.is_at_target(): yield env.timeout(0.01)
                
            stats.log_movement(p_id, 'change_staging', env.now)
            
            # TA returns to desk
            admin.busy = False
            admin.return_home()
            
            # Wait for return walk
            while not admin.is_at_target(): 
                 yield env.timeout(0.01)
            
        else:
            # === Branch B: Porter Free -> Release TA -> Wait for Porter ===
            pass # Exiting 'with' block releases admin
            
    # If Branch B (Porter Free/Called):
    # Check if we need transport (i.e. not at staging yet)
    # Note: Branch A puts us at staging.
    
    # Need to check distance to STAGING now.
    staging_loc = AGENT_POSITIONS['change_staging']
    dist_to_staging = ((patient.x - staging_loc[0])**2 + (patient.y - staging_loc[1])**2)**0.5
    
    if dist_to_staging > 5: # Branch B path (Still at desk or Zone 1)
        # Move to Zone 1 Waiting Grid (Admission to Public Zone)
        arrival_pos, arrival_slot = pos_manager.get_grid_pos('zone1', p_id)
        patient.move_to(*arrival_pos)
        
        # Request Porter (Priority 1)
        with resources['porter'].request(priority=1) as req:
            yield req
            
            # Porter moves to patient
            porter = staff_dict['porter']
            porter.busy = True
            porter.move_to(patient.x, patient.y) # Targets current pos
            
            # Wait for porter to reach patient (Intercept logic)
            while True:
                dist = ((porter.x - patient.x)**2 + (porter.y - patient.y)**2)**0.5
                if dist < 10: break
                porter.move_to(patient.x, patient.y)
                yield env.timeout(0.01)
            
            # Release Zone 1 Grid
            pos_manager.release_pos('zone1', arrival_slot)
            
            # Escort to CHANGE STAGING
            patient.move_to(*staging_loc)
            porter.move_to(*staging_loc)
            while not patient.is_at_target(): yield env.timeout(0.01)
            
            stats.log_movement(p_id, 'change_staging', env.now)
            porter.busy = False
            porter.return_home()

    # ========== Step 5: Change Loop (Seize Logic) ==========
    # Patient is now at Staging.
    
    # Seize a SPECIFIC change room
    change_room_keys = ['change_1', 'change_2', 'change_3']
    
    selected_room = None
    selected_req = None
    
    while selected_room is None:
        # Check for immediate availability
        # Randomize order to verify all rooms get checked and prevent bias to 1 and 2
        # (Fix for observed issue where Room 3 was ignored)
        random.shuffle(change_room_keys)
        
        for key in change_room_keys:
            res = resources[key]
            # STRICT CHECK: resource count must be 0 (empty)
            if res.count < res.capacity:
                selected_room = key
                selected_req = res.request()
                break
        
        if selected_room:
            yield selected_req # Seize it
        else:
            # All full. Wait at staging.
            yield env.timeout(0.5) # Check every 30s sim time
            
    # Move to seized room
    room_target = AGENT_POSITIONS[f"{selected_room}_center"]
    patient.move_to(*room_target)
    while not patient.is_at_target(): yield env.timeout(0.01)
    
    patient.set_state('changing')
    stats.log_state_change(p_id, 'registered', 'changing', env.now)
    yield env.timeout(get_time('changing'))
    
    # Release Room
    resources[selected_room].release(selected_req)
    
    # Move to GOWNED WAITING (Left side of Waiting Room)
    wr_left_pos, wr_left_slot = pos_manager.get_grid_pos('waiting_room_left', p_id)
    patient.move_to(*wr_left_pos)
    while not patient.is_at_target():
        yield env.timeout(0.01)
    
    stats.log_movement(p_id, 'waiting_room', env.now)
    stats.log_waiting_room(p_id, env.now, 'enter')

    # ========== Step 6: Backup Tech Prep ==========
    with resources['backup_techs'].request() as req:
        yield req
        stats.log_waiting_room(p_id, env.now, 'exit')
        
        # Load Balancing Tech Selection
        free_techs = [t for t in staff_dict['backup'] if not t.busy]
        tech = sorted(free_techs, key=lambda t: getattr(t, 'last_used_time', 0))[0] if free_techs else staff_dict['backup'][0]
        
        tech.busy = True
        tech.last_used_time = env.now
        
        # Escort to Prep
        tech.move_to(patient.x, patient.y)
        while not tech.is_at_target(): yield env.timeout(0.01)
        
        pos_manager.release_pos('waiting_room_left', wr_left_slot)
        prep_target = (tech.home_x, tech.home_y)
        
        patient.move_to(*prep_target)
        tech.move_to(*prep_target)
        while not patient.is_at_target(): yield env.timeout(0.01)
        
        stats.log_movement(p_id, 'prep_room', env.now)
        
        # IV Logic
        if random.random() < PROB_IV_NEEDED:
            iv_time = get_time('iv_difficult') if random.random() < PROB_DIFFICULT_IV else get_time('iv_prep')
            yield env.timeout(iv_time)
            
        yield env.timeout(get_time('screening')) # Clinical interview
        
        patient.set_state('prepped')
        stats.log_state_change(p_id, 'changing', 'prepped', env.now)
        
        # Return to Pre-Scan Buffer (Right side)
        wr_right_pos, wr_right_slot = pos_manager.get_grid_pos('waiting_room_right', p_id)
        patient.move_to(*wr_right_pos)
        tech.move_to(*wr_right_pos)
        while not patient.is_at_target(): yield env.timeout(0.01)
        
        stats.log_movement(p_id, 'waiting_room', env.now)
        stats.log_waiting_room(p_id, env.now, 'enter')
        
        tech.busy = False
        tech.return_home()
        
    # ========== Step 7: Pre-Scan Buffer & Washroom ==========
    if random.random() < PROB_WASHROOM_USAGE:
         # Patient decides to use washroom
         pos_manager.release_pos('waiting_room_right', wr_right_slot) # Leave current slot
         
         # Move to Washroom Staging (Zone 2 Hallway)
         patient.move_to(*AGENT_POSITIONS['washroom_staging'])
         while not patient.is_at_target(): yield env.timeout(0.01)
         
         # Seize specific washroom (Staging Logic)
         selected_wr = None
         selected_wr_req = None
         washroom_keys = ['washroom_1', 'washroom_2']
         
         while selected_wr is None:
             for key in washroom_keys:
                 res = resources[key]
                 if res.count < res.capacity:
                     selected_wr = key
                     selected_wr_req = res.request()
                     break
             
             if selected_wr:
                 yield selected_wr_req
             else:
                 yield env.timeout(0.1) # Wait in hallway
         
         # Move into washroom
         wr_target = AGENT_POSITIONS[f"{selected_wr}_center"]
         patient.move_to(*wr_target)
         while not patient.is_at_target(): yield env.timeout(0.01)
         
         stats.log_movement(patient.p_id, 'washroom', env.now)
         yield env.timeout(get_time('washroom'))
         
         # Release Washroom
         resources[selected_wr].release(selected_wr_req)
         
         # Return to Waiting Room (Re-acquire slot)
         # We get a NEW slot as our old one might be taken
         wr_right_pos, wr_right_slot = pos_manager.get_grid_pos('waiting_room_right', p_id) 
         patient.move_to(*wr_right_pos)
         while not patient.is_at_target(): yield env.timeout(0.01)
         
         stats.log_movement(p_id, 'waiting_room', env.now)
         # Ready for scan again

    # ========== Step 8: Autonomous Scan Entry ==========
    magnet_config = yield resources['magnet_pool'].get()
    magnet_res = magnet_config['resource'] # The actual magnet resource
    
    # Seize the magnet
    magnet_req = magnet_res.request()
    yield magnet_req
    
    # Leaving waiting room
    pos_manager.release_pos('waiting_room_right', wr_right_slot)
    stats.log_waiting_room(p_id, env.now, 'exit')
    
    # Walk alone (Digital Signage)
    patient.move_to(*magnet_config['loc'])
    while not patient.is_at_target(): yield env.timeout(0.01)
    
    # ========== Step 9: Scan & Exit ==========
    scan_tech_3t = staff_dict['scan'][0]
    scan_tech_15t = staff_dict['scan'][1] if len(staff_dict['scan']) > 1 else scan_tech_3t
    scan_tech = scan_tech_3t if magnet_config['id'] == '3T' else scan_tech_15t
    
    scan_tech.busy = True
    patient.set_state('scanning')
    stats.log_state_change(p_id, 'prepped', 'scanning', env.now)
    stats.log_movement(p_id, magnet_config['name'], env.now)
    
    # Scan Workflow - Visual: Scanning = Busy (Green)
    magnet_config['visual_state'] = 'busy'
    stats.log_magnet_start(env.now, is_scanning=False)
    yield env.timeout(get_time('scan_setup'))
    stats.log_magnet_end(env.now)
    
    stats.log_magnet_start(env.now, is_scanning=True)
    yield env.timeout(get_time('scan_duration'))
    stats.log_magnet_end(env.now)
    
    # Exit Phase - Request Porter EARLY
    # Visual: Scan Done, Patient Leaving = Dirty (Brown)
    stats.log_completion(p_id, magnet_config['id']) # Increment count immediately
    magnet_config['visual_state'] = 'dirty'
    
    porter_req = resources['porter'].request(priority=0) # High priority
    
    stats.log_magnet_start(env.now, is_scanning=False)
    yield env.timeout(get_time('scan_exit'))
    stats.log_magnet_end(env.now)
    
    # Force patient exit process
    env.process(patient_exit_process(env, patient, renderer, stats, p_id, magnet_config['id'], resources))
    
    # ========== Step 10: The Critical Bed Flip ==========
    yield porter_req
    try:
        stats.log_magnet_start(env.now, is_scanning=False)
        porter = staff_dict['porter']
        porter.busy = True
        
        # Check SMED Condition
        is_same_exam = (magnet_res.last_exam_type == patient.exam_type)
        
        # Visual: Still 'dirty' while being cleaned
        
        if is_same_exam:
            # Fast Flip (Tech assisted)
            # Tech enters room
            scan_tech.move_to(*magnet_config['loc']) 
            porter.move_to(*magnet_config['loc'])
            while not porter.is_at_target(): yield env.timeout(0.01)
            
            yield env.timeout(get_time('bed_flip_fast'))
            
            # Tech returns to control
            scan_tech.return_home() # This needs to be defined for scan techs or they stay put
             
        else:
            # Slow Flip (Porter Solo + Tech Settings Change)
            # Tech stays in control room (Zone 3)
            # Porter moves to magnet
            porter.move_to(*magnet_config['loc'])
            while not porter.is_at_target(): yield env.timeout(0.01)
            
            # Parallel Tasks: Porter cleans vs Tech changes software
            t_porter = get_time('bed_flip_slow')
            t_tech = get_time('settings_change')
            duration = max(t_porter, t_tech)
            
            yield env.timeout(duration)
            
        # Update last exam type
        magnet_res.last_exam_type = patient.exam_type
        # Visual: Clean (White) after flip done
        magnet_config['visual_state'] = 'clean' 
        
        stats.log_magnet_end(env.now)
        
        porter.busy = False
        porter.return_home()
        
    finally:
        resources['porter'].release(porter_req)
        
    # Release Magnet Resource & Pool
    scan_tech.busy = False
    # If tech moved to magnet, they need to return to staging
    scan_tech.return_home()
    
    magnet_res.release(magnet_req)
    yield resources['magnet_pool'].put(magnet_config)

def patient_generator(env, staff_dict, resources, stats, renderer, duration):
    """
    Generate patients at scheduled intervals with Smart Gatekeeper Logic.
    Stops accepting new patients when queue burden exceeding remaining time.
    """
    from src.visuals.sprites import Patient
    
    p_id = 0
    stats.generator_active = True
    
    while True:
        # Smart Gatekeeper Logic
        # Estimate time to clear current system
        # Assuming 2 magnets working in parallel
        # Burden = (Patients * Avg Time) / Magnets
        magnet_count = 2
        queue_burden = (stats.patients_in_system * config.AVG_CYCLE_TIME) / magnet_count
        stats.est_clearing_time = queue_burden
        
        time_remaining = duration - env.now
        
        # Closing Condition:
        # If we need more time to clear current patients than we have left in the shift,
        # we strictly close the gate.
        # We also add a small buffer (MAX_SCAN_TIME) to ensure the last patient can finish reasonably.
        if (queue_burden > time_remaining) or (env.now > duration - config.MAX_SCAN_TIME and stats.patients_in_system > 0):
             print(f"Gatekeeper Closing at {env.now:.1f}m: Queue Burden {queue_burden:.1f}m > Time Left {time_remaining:.1f}m")
             stats.generator_active = False
             break
        
        if env.now >= duration:
             stats.generator_active = False
             break
        
        p_id += 1
        
        # Create patient sprite
        patient = Patient(p_id, *AGENT_POSITIONS['zone1_center'])
        # Assign Exam Type (Source 140)
        patient.exam_type = random.choice(EXAM_TYPES)
        
        renderer.add_sprite(patient)
        
        # Start patient journey
        env.process(patient_journey(env, patient, staff_dict, resources, stats, renderer))
        
        # Wait for next patient
        inter_arrival = poisson_sample(PROCESS_TIMES['mean_inter_arrival'])
        yield env.timeout(inter_arrival)
        
    stats.generator_active = False
