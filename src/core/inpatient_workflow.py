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
    patient.arrival_time = env.now
    stats.log_state_change(p_id, None, 'arriving', env.now)
    
    # Step 2: Move directly to Holding/Transfer Room 311 (using slots)
    # Capacity Check
    room_311_res = resources.get('room_311')
    if room_311_res:
         with room_311_res.request() as req:
            yield req
            
            # Find free slot visually (basic toggle for simplicity or random free)
            # For strict slot tracking we'd need a resource per slot, but simple toggle works visually
            slot_idx = random.randint(0, 1) 
            slot_key = f'room_311_slot_{slot_idx+1}'
            target_loc = AGENT_POSITIONS.get(slot_key, (450, 350))
            
            patient.move_to(*target_loc)
            while not patient.is_at_target():
                yield env.timeout(0.01)
            
            # State Change: IMMEDIATELY prepped (Yellow)
            patient.set_state('prepped') 
            stats.log_state_change(p_id, 'arriving', 'prepped', env.now)
            stats.log_movement(p_id, 'holding_transfer', env.now)
            
            # Step 3: Perform prep (anesthesia setup)
            # Parallel processing: Anesthesia prep outside magnet
            patient.start_timer('holding_room', env.now)
            prep_time = get_time('holding_prep')
            yield env.timeout(prep_time)
            patient.stop_timer('holding_room', env.now)
        
            # Step 4: Wait for magnet (with HIGH PRIORITY)
            # 4a. Request priority access to the magnet pool (Priority 0)
            patient.start_timer('wait_room', env.now)
            access_req = resources['magnet_access'].request(priority=config.PRIORITY_INPATIENT)
            yield access_req
            patient.stop_timer('wait_room', env.now)
            
            # 4b. Actually get a specific magnet from the available pool
            magnet_config = yield resources['magnet_pool'].get()
            magnet_res = magnet_config['resource']
            
            # Seize the specific magnet resource
            magnet_req = magnet_res.request(priority=config.PRIORITY_INPATIENT)
            yield magnet_req
            
            # Step 5: Bed transfer to magnet
            patient.start_timer('holding_room', env.now) # Transfer counts as holding egress
            transfer_time = get_time('bed_transfer')
            patient.move_to(*magnet_config['loc'])
            yield env.timeout(transfer_time)
            patient.stop_timer('holding_room', env.now)
            while not patient.is_at_target():
                yield env.timeout(0.01)
            
            # Step 6: Scan (simplified for inpatients - no separate setup)
            # Determine active scan tech (supporting cross-coverage)
            staff_mgr = resources.get('staff_mgr')
            tech_idx = 0 if magnet_config['id'] == '3T' else 1
            is_on_break = getattr(staff_mgr, 'scan_coverage_status', {}).get(tech_idx, False) if staff_mgr else False
            
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
            
            magnet_config['visual_state'] = 'busy'
            stats.log_magnet_start(env.now, is_scanning=True)
            patient.start_timer('scan_room', env.now)
            
            scan_time = get_time('scan_duration')
            yield env.timeout(scan_time)
            
            stats.log_magnet_metric(magnet_config['id'], 'scan', scan_time)
            patient.stop_timer('scan_room', env.now)
            stats.log_magnet_end(env.now)
            
            # Step 7: Exit - Inpatient Porter Assist Logic
            magnet_config['visual_state'] = 'dirty'
            
            # Inpatient Egress: Require Porter to move patient out
            porter_req = resources['porter'].request(priority=0)
            yield porter_req
            
            porter = staff_dict['porter']
            porter.busy = True
            
            # Porter moves to magnet to collect patient
            porter.move_to(*magnet_config['loc'])
            while not porter.is_at_target():
                yield env.timeout(0.01)
                
            # Escort to Exit
            patient.set_state('exited')
            stats.log_state_change(p_id, 'scanning', 'exited', env.now)
            
            # Both move to exit
            exit_loc = AGENT_POSITIONS['exit']
            patient.move_to(*exit_loc)
            porter.move_to(*exit_loc)
            
            # Visual: Room becomes clean/white as they leave
            magnet_config['visual_state'] = 'clean'
            
            while not patient.is_at_target():
                yield env.timeout(0.01)
                
            renderer.remove_sprite(patient)
            stats.log_movement(p_id, 'exit', env.now)
            stats.log_patient_finished(patient, env.now)
            
            # Porter returns to base
            porter.busy = False
            porter.return_home()
            resources['porter'].release(porter_req)
            
            # Magnet Release (Happens AFTER patient is gone)
            scan_tech.busy = False
            scan_tech.return_home()
            magnet_res.release(magnet_req)
            resources['magnet_access'].release(access_req)
            yield resources['magnet_pool'].put(magnet_config)
