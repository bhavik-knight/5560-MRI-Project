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

def handle_no_show_gap(env, resources, stats, wait_time):
    """
    Simulates a magnet slot lost to a no-show.
    The slot sits idle for X minutes before staff releases it.
    """
    # Request a magnet access slot
    access_req = resources['magnet_access'].request(priority=1)
    yield access_req
    
    # Take a magnet from the pool
    magnet_config = yield resources['magnet_pool'].get()
    m_id = magnet_config['id']
    
    # Sits idle
    yield env.timeout(wait_time)
    
    # Log the waste specifically
    stats.log_magnet_metric(m_id, 'noshow', wait_time)
    
    # Release back to pool
    resources['magnet_access'].release(access_req)
    yield resources['magnet_pool'].put(magnet_config)

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
    
    # Seize Change Room (competing with incoming patients) - Optimized
    selected_room = None
    selected_req = None
    
    while selected_room is None:
        # Use helper for immediate availability check
        available_room = resources['get_free_change_room']()
        
        if available_room:
            selected_room = available_room
            selected_req = resources[selected_room].request()
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
    patient.start_timer('change', env.now)
    yield env.timeout(get_time('change_back'))
    patient.stop_timer('change', env.now)
    
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
    stats.log_patient_finished(patient, env.now)

def patient_journey(env, patient, staff_dict, resources, stats, renderer):
    """
    Implements the "Pit Crew" workflow with conditional staff logic.
    Now includes branching for Inpatient (high acuity) vs Outpatient workflows.
    """
    from src.core.inpatient_workflow import inpatient_workflow
    
    p_id = patient.p_id
    
    # ========== Step -0.1: Compliance Check (Lateness) ==========
    if getattr(patient, 'is_late', False) and patient.late_duration > 0:
        # Scheduled arrival was now
        # If magnet is currently empty, this person is idling the system
        magnet_pool_idle_count = len(resources['magnet_pool'].items)
        if magnet_pool_idle_count == 2: # Both magnets idle
             stats.log_magnet_metric('3T', 'lateness', patient.late_duration)
        elif magnet_pool_idle_count == 1:
             m_config = resources['magnet_pool'].items[0]
             stats.log_magnet_metric(m_config['id'], 'lateness', patient.late_duration)
             
        yield env.timeout(patient.late_duration)
    
    # Actually arrive now
    renderer.add_sprite(patient)

    # ========== Step 0: Patient Classification ==========
    is_inpatient = random.random() < config.PROB_INPATIENT
    patient.patient_type = 'inpatient' if is_inpatient else 'outpatient'
    
    selected_room = None
    selected_req = None
    escorted = False
    
    if is_inpatient:
        patient.color = config.COLOR_INPATIENT  # Dark Pink
        # Inpatient path: bypass registration, go to holding room
        yield from inpatient_workflow(env, patient, staff_dict, resources, stats, renderer, p_id)
        return  # Exit after inpatient workflow completes
    else:
        patient.color = config.COLOR_OUTPATIENT  # Dodger Blue
        patient.arrival_time = env.now
    
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

        # WAIT FOR ADMIN TA OR COVERING PORTER (Physical Presence Check)
        staff_mgr = resources.get('staff_mgr')
        is_covered = getattr(staff_mgr, 'porter_covering_admin', False) if staff_mgr else False
        active_staff = staff_dict['porter'] if is_covered else staff_dict['admin']
        
        while not active_staff.is_at_target():
             dist_admin = ((active_staff.x - admin_x)**2 + (active_staff.y - admin_y)**2)**0.5
             if dist_admin < 5: break
             yield env.timeout(0.01)
             
        # Now Registration Process
        patient.color = PURPLE_REGISTERED
        stats.log_state_change(p_id, 'arriving', 'registered', env.now)
        patient.start_timer('admin', env.now)
        yield env.timeout(get_time('registration'))
        patient.stop_timer('admin', env.now)
        
        # ========== Step 3 & 4: Transport Decision (Human Factors Coverage) ==========
        porter_res = resources['porter']
        staff_mgr = resources.get('staff_mgr')
        porter_on_break = getattr(staff_mgr, 'staff_on_break', {}).get('porter_0', False) if staff_mgr else False
        porter_covering = getattr(staff_mgr, 'porter_covering_admin', False) if staff_mgr else False
        
        # Decision: Use Admin station or Tech if Porter is busy/on-break/covering
        if (porter_res.count >= porter_res.capacity or len(porter_res.queue) > 0 or 
            porter_on_break or porter_covering):
            
            # --- Option A: Admin Station Escorts ---
            # If porter is covering admin, they are at the desk!
            is_p_at_desk = porter_covering
            escort_staff = staff_dict['porter'] if is_p_at_desk else staff_dict['admin']
            
            escort_staff.busy = True
            
            # AT ARRIVAL: Dynamic Look-Ahead
            free_room, _ = resources['get_free_change_room_with_index']()
            if free_room:
                selected_room = free_room
                selected_req = resources[selected_room].request()
                yield selected_req
                change_target = AGENT_POSITIONS[f"{selected_room}_center"]
                stats.log_movement(p_id, 'change_room', env.now)
            else:
                change_target = AGENT_POSITIONS['change_staging']
                stats.log_movement(p_id, 'change_staging', env.now)
                
            # Escort to destination
            patient.move_to(*change_target)
            escort_staff.move_to(*change_target)
            while not patient.is_at_target(): yield env.timeout(0.01)
            
            escorted = True
            escort_staff.busy = False
            
            # Return to station
            # Re-check live coverage status (break might have ended during task)
            still_covering = getattr(staff_mgr, 'porter_covering_admin', False) if staff_mgr else False
            
            if is_p_at_desk and still_covering:
                escort_staff.cover_position(AGENT_POSITIONS['admin_home'])
            else:
                escort_staff.return_home()
            
        else:
            # === Branch B: Wait for Porter arriving in next block ===
            pass
            
    # Case 1 & 4 Coverage: Allow tech to process 'transport' event if porter unavailable
    if not escorted:
        # Move to Zone 1 Waiting Grid
        arrival_pos, arrival_slot = pos_manager.get_grid_pos('zone1', p_id)
        patient.move_to(*arrival_pos)
        
        staff_mgr = resources.get('staff_mgr')
        porter_avail = not getattr(staff_mgr, 'staff_on_break', {}).get('porter_0', False) and not getattr(staff_mgr, 'porter_covering_admin', False)
        
        if not porter_avail and resources['backup_techs'].count < resources['backup_techs'].capacity:
            # === Branch C: Tech Escorts ===
            with resources['backup_techs'].request() as b_req:
                yield b_req
                # Find free backup tech
                free_backups = [t for t in staff_dict['backup'] if not t.busy]
                if free_backups:
                    tech = free_backups[0]
                    tech.busy = True
                    
                    # Move to patient
                    tech.move_to(patient.x, patient.y)
                    while not tech.is_at_target(): yield env.timeout(0.01)
                    
                    # Transport decision
                    free_room, _ = resources['get_free_change_room_with_index']()
                    if free_room:
                        selected_room = free_room
                        selected_req = resources[selected_room].request()
                        yield selected_req
                        change_target = AGENT_POSITIONS[f"{selected_room}_center"]
                    else:
                        change_target = AGENT_POSITIONS['change_staging']
                    
                    pos_manager.release_pos('zone1', arrival_slot)
                    patient.move_to(*change_target)
                    tech.move_to(*change_target)
                    while not patient.is_at_target(): yield env.timeout(0.01)
                    
                    tech.busy = False
                    tech.return_home()
                    escorted = True

        if not escorted:
            # Wait for Porter (Priority 1)
            with resources['porter'].request(priority=1) as req:
                yield req
                
                porter = staff_dict['porter']
                porter.busy = True
                
                # Porter moves to patient
                while True:
                    dist = ((porter.x - patient.x)**2 + (porter.y - patient.y)**2)**0.5
                    if dist < 10: break
                    porter.move_to(patient.x, patient.y)
                    yield env.timeout(0.01)
                    
                # AT ARRIVAL: Dynamic Look-Ahead
                free_room, _ = resources['get_free_change_room_with_index']()
                if free_room:
                    selected_room = free_room
                    selected_req = resources[selected_room].request()
                    yield selected_req
                    change_target = AGENT_POSITIONS[f"{selected_room}_center"]
                    stats.log_movement(p_id, 'change_room', env.now)
                else:
                    change_target = AGENT_POSITIONS['change_staging']
                    stats.log_movement(p_id, 'change_staging', env.now)
                
                # Release Zone 1 Grid
                pos_manager.release_pos('zone1', arrival_slot)
                
                # Escort to destination
                patient.move_to(*change_target)
                porter.move_to(*change_target)
                while not patient.is_at_target(): yield env.timeout(0.01)
                
                porter.busy = False
                porter.return_home()

    # ========== Step 5: Smart Seize (Skip if Already Seized) ==========
    # If room was seized during transport, skip seizing
    
    if selected_room is None:
        # Need to seize a room (we're at staging)
        while selected_room is None:
            # Look-ahead: Check if ANY room is free
            free_room, _ = resources['get_free_change_room_with_index']()
            
            if free_room:
                # Room available! Seize it immediately
                selected_room = free_room
                selected_req = resources[selected_room].request()
                yield selected_req
                break
            else:
                # ALL rooms occupied - wait at staging
                yield env.timeout(0.5)
                
        # Move to seized room from staging
        room_target = AGENT_POSITIONS[f"{selected_room}_center"]
        patient.move_to(*room_target)
        while not patient.is_at_target(): yield env.timeout(0.01)
        stats.log_movement(p_id, 'change_room', env.now)
    # else: Already at room, seized during transport
    
    # Change into gown
    patient.set_state('changing')
    stats.log_state_change(p_id, 'registered', 'changing', env.now)
    patient.start_timer('change', env.now)
    yield env.timeout(get_time('changing'))
    patient.stop_timer('change', env.now)
    
    # Release Room
    resources[selected_room].release(selected_req)
    
    # Move to GOWNED WAITING (Left side of Waiting Room)
    wr_left_pos, wr_left_slot = pos_manager.get_grid_pos('waiting_room_left', p_id)
    patient.move_to(*wr_left_pos)
    while not patient.is_at_target():
        yield env.timeout(0.01)
    
    stats.log_movement(p_id, 'waiting_room', env.now)
    stats.log_waiting_room(p_id, env.now, 'enter')
    patient.start_timer('wait_room', env.now)

    # ========== Step 6: Backup Tech Prep ==========
    with resources['backup_techs'].request() as req:
        yield req
        patient.stop_timer('wait_room', env.now)
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
        patient.start_timer('prep', env.now)
        if random.random() < PROB_IV_NEEDED:
            patient.has_iv = True
            iv_time = get_time('iv_difficult') if random.random() < PROB_DIFFICULT_IV else get_time('iv_prep')
            if random.random() < PROB_DIFFICULT_IV: patient.is_difficult = True
            yield env.timeout(iv_time)
            
        yield env.timeout(get_time('screening')) # Clinical interview
        patient.stop_timer('prep', env.now)
        
        patient.set_state('prepped')
        stats.log_state_change(p_id, 'changing', 'prepped', env.now)
        
        # Return to Pre-Scan Buffer (Right side)
        wr_right_pos, wr_right_slot = pos_manager.get_grid_pos('waiting_room_right', p_id)
        patient.move_to(*wr_right_pos)
        tech.move_to(*wr_right_pos)
        while not patient.is_at_target(): yield env.timeout(0.01)
        
        stats.log_movement(p_id, 'waiting_room', env.now)
        stats.log_waiting_room(p_id, env.now, 'enter')
        patient.start_timer('wait_room', env.now)
        
        tech.busy = False
        tech.return_home()
        
    # ========== Step 7: Pre-Scan Buffer & Washroom (Smart Seize) ==========
    if random.random() < PROB_WASHROOM_USAGE:
         # Patient decides to use washroom
         
         selected_wr = None
         selected_wr_req = None
         at_wr_staging = False
         
         # Look-ahead: Check availability while in waiting room
         while selected_wr is None:
             free_wr, free_idx = resources['get_free_washroom_with_index']()
             
             if free_wr:
                 # Washroom available! Seize it
                 selected_wr = free_wr
                 selected_wr_req = resources[selected_wr].request()
                 yield selected_wr_req
                 # Release waiting room slot and go directly
                 pos_manager.release_pos('waiting_room_right', wr_right_slot)
                 break
             else:
                 # ALL washrooms occupied
                 if not at_wr_staging:
                     # Move to WASHROOM staging (spatial separation from change staging)
                     pos_manager.release_pos('waiting_room_right', wr_right_slot)
                     patient.move_to(*AGENT_POSITIONS['washroom_staging'])
                     while not patient.is_at_target():
                         yield env.timeout(0.01)
                     at_wr_staging = True
                 # Wait at washroom staging
                 yield env.timeout(0.1)
         
         # Move into washroom (directly if was in waiting room, from staging if was waiting)
         wr_target = AGENT_POSITIONS[f"{selected_wr}_center"]
         patient.move_to(*wr_target)
         while not patient.is_at_target(): yield env.timeout(0.01)
         
         stats.log_movement(patient.p_id, 'washroom', env.now)
         patient.start_timer('washroom', env.now)
         yield env.timeout(get_time('washroom'))
         patient.stop_timer('washroom', env.now)
         
         # Release Washroom
         resources[selected_wr].release(selected_wr_req)
         
         # Return to Waiting Room (Re-acquire slot)
         wr_right_pos, wr_right_slot = pos_manager.get_grid_pos('waiting_room_right', p_id) 
         patient.move_to(*wr_right_pos)
         while not patient.is_at_target(): yield env.timeout(0.01)
         
         stats.log_movement(p_id, 'waiting_room', env.now)
         # Ready for scan again

    # ========== Step 8: Autonomous Scan Entry ==========
    # 8a. Request priority access to the magnet pool (Priority 1)
    access_req = resources['magnet_access'].request(priority=config.PRIORITY_OUTPATIENT)
    yield access_req
    patient.stop_timer('wait_room', env.now)
    
    # 8b. Get first available magnet
    magnet_config = yield resources['magnet_pool'].get()
    magnet_res = magnet_config['resource'] # The actual magnet resource
    
    # Seize the specific magnet resource
    magnet_req = magnet_res.request(priority=config.PRIORITY_OUTPATIENT)
    yield magnet_req
    
    # Leaving waiting room
    pos_manager.release_pos('waiting_room_right', wr_right_slot)
    stats.log_waiting_room(p_id, env.now, 'exit')
    
    # 8c. Walk to Magnet (Outpatients assume 'Signage' navigation)
    patient.move_to(*magnet_config['loc'])
    while not patient.is_at_target(): yield env.timeout(0.01)
    
    
    # Determine active scan tech (supporting cross-coverage)
    staff_mgr = resources.get('staff_mgr')
    tech_idx = 0 if magnet_config['id'] == '3T' else 1
    is_on_break = getattr(staff_mgr, 'staff_on_break', {}).get(f"scan_{tech_idx}", False) if staff_mgr else False
    
    if is_on_break:
        # Cross-coverage: Use backup tech (staying cyan visually)
        scan_tech = staff_dict['backup'][tech_idx % len(staff_dict['backup'])]
    else:
        scan_tech_3t = staff_dict['scan'][0]
        scan_tech_15t = staff_dict['scan'][1] if len(staff_dict['scan']) > 1 else scan_tech_3t
        scan_tech = scan_tech_3t if magnet_config['id'] == '3T' else scan_tech_15t
    
    scan_tech.busy = True
    patient.set_state('scanning')
    stats.log_state_change(p_id, 'prepped', 'scanning', env.now)
    stats.log_movement(p_id, magnet_config['name'], env.now)
    patient.start_timer('scan_room', env.now)
    
    # Scan Workflow - Visual: Scanning = Busy (Green)
    magnet_config['visual_state'] = 'busy'
    stats.log_magnet_start(env.now, is_scanning=False)
    
    # SETUP (Brown)
    setup_time = get_time('scan_setup')
    yield env.timeout(setup_time)
    stats.log_magnet_metric(magnet_config['id'], 'setup', setup_time)
    stats.log_magnet_end(env.now)
    
    # SCAN (Green)
    stats.log_magnet_start(env.now, is_scanning=True)
    scan_time = get_time('scan_duration')
    yield env.timeout(scan_time)
    stats.log_magnet_metric(magnet_config['id'], 'scan', scan_time)
    stats.log_magnet_end(env.now)
    
    # Exit Phase - Request Porter EARLY
    # Visual: Scan Done, Patient Leaving = Dirty (Brown)
    stats.log_magnet_start(env.now, is_scanning=False)
    exit_time = get_time('scan_exit')
    yield env.timeout(exit_time)
    stats.log_magnet_metric(magnet_config['id'], 'exit', exit_time)
    stats.log_magnet_end(env.now)
    
    patient.stop_timer('scan_room', env.now)
    magnet_config['visual_state'] = 'dirty'
    
    porter_req = resources['porter'].request(priority=0) # High priority
    
    # Force patient exit process
    env.process(patient_exit_process(env, patient, renderer, stats, p_id, magnet_config['id'], resources))
    
    # ========== Step 10: The Critical Bed Flip ==========
    # ========== Step 10: The Critical Bed Flip ==========
    yield porter_req
    try:
        stats.log_magnet_start(env.now, is_scanning=False)
        porter = staff_dict['porter']
        porter.busy = True

        # Safety: Wait for patient to physically clear the room (Visual)
        # Assuming magnet radius ~40-50, wait for 60px distance
        mx, my = magnet_config['loc']
        while ((patient.x - mx)**2 + (patient.y - my)**2)**0.5 < 60:
            yield env.timeout(0.5)
        
        # Check SMED Condition
        is_same_exam = (magnet_res.last_exam_type == patient.exam_type)
        
        # Visual: Still 'dirty' while being cleaned
        
        if is_same_exam:
            # Fast Flip (Tech assisted)
            # Tech enters room
            scan_tech.move_to(*magnet_config['loc']) 
            porter.move_to(*magnet_config['loc'])
            while not porter.is_at_target(): yield env.timeout(0.01)
            
            flip_time = get_time('bed_flip_fast')
            yield env.timeout(flip_time)
            stats.log_magnet_metric(magnet_config['id'], 'flip', flip_time)
            patient.metrics['bed_flip'] = flip_time  # Log to patient metrics for summary
            
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
            stats.log_magnet_metric(magnet_config['id'], 'flip', duration)
            patient.metrics['bed_flip'] = duration  # Log to patient metrics for summary
            
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
    resources['magnet_access'].release(access_req)
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
        
        # Determine fate immediately: No-Show, Late, or Normal
        fate_roll = random.random()
        is_noshow = fate_roll < config.PROB_NO_SHOW
        is_late = (not is_noshow) and (fate_roll < config.PROB_NO_SHOW + config.PROB_LATE)
        
        if is_noshow:
            # Simulate the lost gap
            env.process(handle_no_show_gap(env, resources, stats, config.PROCESS_TIMES['no_show_wait']))
        else:
            # Create patient sprite
            patient = Patient(p_id, *AGENT_POSITIONS['zone1_center'])
            patient.exam_type = random.choice(EXAM_TYPES)
            
            # Compliance tracking
            patient.is_late = is_late
            patient.late_duration = 0
            if is_late:
                patient.late_duration = triangular_sample(config.PROCESS_TIMES['late_delay'])
                stats.late_arrivals += 1

            # Start patient journey (renderer.add_sprite handled inside journey after delay)
            env.process(patient_journey(env, patient, staff_dict, resources, stats, renderer))
        
        # Wait for next patient inter-arrival
        inter_arrival = poisson_sample(PROCESS_TIMES['mean_inter_arrival'])
        yield env.timeout(inter_arrival)
        
    stats.generator_active = False
