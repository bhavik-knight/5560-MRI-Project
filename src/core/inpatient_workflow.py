"""
Inpatient Workflow Module
==========================
Handles high-acuity inpatient workflow that bypasses standard registration.
"""

import random
import src.config as config
from src.config import AGENT_POSITIONS

def get_time(task):
    """Sample from triangular distribution."""
    return random.triangular(*config.PROCESS_TIMES[task])

def inpatient_workflow(env, patient, staff_dict, resources, stats, renderer, p_id):
    """
    High-acuity inpatient workflow: Bypass registration, go directly to Holding Room 311.
    """
    # Step 1: Arrival (no registration)
    patient.set_state('arriving')
    stats.log_state_change(p_id, None, 'arriving', env.now)
    
    # Step 2: Move directly to Holding/Transfer Room 311
    holding_loc = AGENT_POSITIONS['holding_transfer_center']
    patient.move_to(*holding_loc)
    while not patient.is_at_target():
        yield env.timeout(0.01)
    
    stats.log_movement(p_id, 'holding_transfer', env.now)
    
    # Step 3: Seize holding room and perform prep (anesthesia setup)
    with resources['holding_room'].request() as req:
        yield req
        
        patient.set_state('prepped')  # Use prepped state for inpatients in holding
        stats.log_state_change(p_id, 'arriving', 'prepped', env.now)
        
        # Parallel processing: Anesthesia prep outside magnet
        prep_time = get_time('holding_prep')
        yield env.timeout(prep_time)
    
    # Step 4: Wait for magnet (with HIGH PRIORITY)
    # 4a. Request priority access to the magnet pool (Priority 0)
    access_req = resources['magnet_access'].request(priority=config.PRIORITY_INPATIENT)
    yield access_req
    
    # 4b. Actually get a specific magnet from the available pool
    magnet_config = yield resources['magnet_pool'].get()
    magnet_res = magnet_config['resource']
    
    # Seize the specific magnet resource
    magnet_req = magnet_res.request(priority=config.PRIORITY_INPATIENT)
    yield magnet_req
    
    # Step 5: Bed transfer to magnet
    transfer_time = get_time('bed_transfer')
    patient.move_to(*magnet_config['loc'])
    yield env.timeout(transfer_time)
    while not patient.is_at_target():
        yield env.timeout(0.01)
    
    # Step 6: Scan (simplified for inpatients - no separate setup)
    scan_tech_3t = staff_dict['scan'][0]
    scan_tech_15t = staff_dict['scan'][1] if len(staff_dict['scan']) > 1 else scan_tech_3t
    scan_tech = scan_tech_3t if magnet_config['id'] == '3T' else scan_tech_15t
    
    scan_tech.busy = True
    patient.set_state('scanning')
    stats.log_state_change(p_id, 'prepped', 'scanning', env.now)
    stats.log_movement(p_id, magnet_config['name'], env.now)
    
    magnet_config['visual_state'] = 'busy'
    stats.log_magnet_start(env.now, is_scanning=True)
    yield env.timeout(get_time('scan_duration'))
    stats.log_magnet_end(env.now)
    
    # Step 7: Exit (inpatients exit directly, no change room)
    stats.log_completion(p_id, magnet_config['id'])
    magnet_config['visual_state'] = 'dirty'
    
    # Bed flip
    porter_req = resources['porter'].request(priority=0)
    yield porter_req
    try:
        stats.log_magnet_start(env.now, is_scanning=False)
        porter = staff_dict['porter']
        porter.busy = True
        porter.move_to(*magnet_config['loc'])
        while not porter.is_at_target():
            yield env.timeout(0.01)
        
        yield env.timeout(get_time('bed_flip_slow'))
        magnet_config['visual_state'] = 'clean'
        stats.log_magnet_end(env.now)
        porter.busy = False
        porter.return_home()
    finally:
        resources['porter'].release(porter_req)
    
    scan_tech.busy = False
    scan_tech.return_home()
    magnet_res.release(magnet_req)
    resources['magnet_access'].release(access_req)
    yield resources['magnet_pool'].put(magnet_config)
    
    # Exit directly
    patient.set_state('exited')
    stats.log_state_change(p_id, 'scanning', 'exited', env.now)
    patient.move_to(*AGENT_POSITIONS['exit'])
    while not patient.is_at_target():
        yield env.timeout(0.01)
    renderer.remove_sprite(patient)
    stats.log_movement(p_id, 'exit', env.now)
