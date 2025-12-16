
import simpy
import random
import statistics
import pandas as pd
try:
    from src.config import MRI_Config
except ImportError:
    from config import MRI_Config

# Global config
config = MRI_Config()

class MRI_Stat_Tracker:
    def __init__(self):
        self.throughput = 0
        self.magnet_busy_time = 0.0
        # For Gantt Chart: list of dicts {Start, Finish, Resource, State}
        self.event_log = [] 

class Patient:
    def __init__(self, p_id):
        self.id = p_id
        self.state = 'Arrived/Waiting' # Initial State
        self.x = 0
        self.y = 0

def get_triangular_sample(triangular_tuple):
    # triangular_tuple is (low, mode, high)
    return random.triangular(triangular_tuple[0], triangular_tuple[2], triangular_tuple[1])

def get_normal_sample(normal_tuple):
    # normal_tuple is (mu, sigma)
    val = random.gauss(normal_tuple[0], normal_tuple[1])
    return max(0, val)

def monitor_process(env, all_patients, animation_data):
    """
    Runs every 1 minute.
    Snapshot Logic: Check status of every patient and assign (x, y).
    """
    while True:
        minute = env.now
        
        for p in all_patients:
            # Logic based on state
            if p.state == 'Arrived/Waiting':
                # Zone 1 (Waiting): x=0, y=random(0,5)
                p.x = 0
                p.y = random.uniform(0, 5)
            elif p.state == 'Prepping' or p.state == 'IV Setup':
                # Zone 2 (Prep): x=1, y=random(0,5)
                p.x = 1
                p.y = random.uniform(0, 5)
            elif p.state == 'Scanning':
                # Zone 4 (Magnet): x=2, y=2 (Capacity 1)
                p.x = 2
                p.y = 2
            elif p.state == 'Done':
                # Exit: x=3, y=random(0,5)
                p.x = 3
                p.y = random.uniform(0, 5)
            # If 'Done' creates too many points accumulating, we might want to filter finished patients eventually,
            # but for a 12h sim it's fine.
            
            animation_data.append({
                'Minute': minute,
                'Patient_ID': p.id,
                'X': p.x,
                'Y': p.y,
                'State': p.state
            })
            
        yield env.timeout(1)

def handle_patient(env, patient, magnet, prep_staff, stats, parallel_prep, bed_flip_time):
    # --- PROCESS START ---
    
    # 1. Arrival / Waiting
    patient.state = 'Arrived/Waiting'
    
    screening_dur = get_triangular_sample(config.screening_time)
    change_dur = get_triangular_sample(config.change_time)
    needs_iv = (random.random() < config.prob_needs_IV)
    iv_dur = get_triangular_sample(config.iv_setup_time) if needs_iv else 0.0
    total_prep_time = screening_dur + change_dur + iv_dur

    scan_dur = get_normal_sample(config.scan_duration)

    if not parallel_prep:
        # --- SCENARIO A: SERIAL (Current State) ---
        # Logic: Arrive -> Seize Magnet -> Do Prep (Inside) -> Scan -> Bed Flip -> Release
        
        # Wait for Magnet (Patient in Zone 1)
        with magnet.request() as req:
            yield req
            # Got Magnet. Move to Prep physically (Zone 2/3 but acts as Magnet room block).
            # Prompt: "Seize Magnet -> Do Prep (inside room)".
            # So effectively patient is occupying Magnet resource.
            # Tracking state:
            patient.state = 'Prepping'
            
            # Log Prep as "Idle/Waste" for the machine
            start_prep = env.now
            yield env.timeout(total_prep_time)
            stats.event_log.append({
                'Start': start_prep, 'Finish': env.now, 
                'Resource': 'Magnet', 'State': 'Idle (Prep)'
            })
            
            # Scan
            patient.state = 'Scanning'
            start_scan = env.now
            yield env.timeout(scan_dur)
            stats.event_log.append({
                'Start': start_scan, 'Finish': env.now, 
                'Resource': 'Magnet', 'State': 'Scanning'
            })
            
            stats.magnet_busy_time += scan_dur
            stats.throughput += 1
            
            # Bed Flip (Serial)
            # Patient acts as 'Done' or 'Leaving' during flip? 
            # Usually flip happens after patient leaves.
            patient.state = 'Done'
            start_flip = env.now
            yield env.timeout(bed_flip_time) # 5 mins default
            stats.event_log.append({
                'Start': start_flip, 'Finish': env.now, 
                'Resource': 'Magnet', 'State': 'Changeover'
            })

    else:
        # --- SCENARIO B: PARALLEL (Future State) ---
        # Logic: Arrive -> Seize Prep (Zone 2) -> Do Prep -> Wait Magnet -> Seize Magnet -> Scan -> Release
        
        # Seize Prep Staff (Zone 2)
        with prep_staff.request() as req_staff:
            yield req_staff
            
            patient.state = 'Prepping'
            yield env.timeout(total_prep_time)
            
            # Prep Done. Wait for Magnet.
            # Ideally release staff? check logic: "Wait for Magnet -> Seize Magnet".
            # Usually you hold the "Gowned Waiting" spot? Or just wait in Zone 2?
            # Prompt: "Seize Prep_Room -> Do Prep -> Wait for Magnet -> Seize Magnet".
            # Implies we hold the prep room (or zone 2 slot) until we get the magnet.
            # But "Staff" might be free?
            # Let's assume we hold the resource to represent "Occupying Zone 2".
            
            patient.state = 'Arrived/Waiting' # Waiting Gowned? Let's keep 'Prepping' or 'IV Setup' or 'Ready'?
            # Zone 2 logic says "If stats is Prepping or IV Setup".
            # Let's keep state as 'Prepping' (meaning In Prep Zone) effectively. 
            
            # Seize Magnet
            with magnet.request() as req_magnet:
                yield req_magnet
                
                # Release Prep/Staff (we moved to Zone 4)
                # But we are inside the `with prep_staff` block? 
                # SimPy `with` releases at END of block. 
                # We need to explicitly release if we want to release *during* nested.
                # It's cleaner to break the `with` if we want handoff.
                pass 
            # This nested structure holds Staff until Magnet is done? That's WRONG.
            # Let's re-write non-nested.
            
        # Non-nested Parallel Flow
        req_staff = prep_staff.request()
        yield req_staff
        
        patient.state = 'Prepping'
        yield env.timeout(total_prep_time)
        
        # Done Prep. Now Wait for Magnet. 
        # State? Still in Zone 2.
        
        req_magnet = magnet.request()
        yield req_magnet
        
        # Ensure we log "Wait time" if any? (Implicit in simulation clock)
        
        # Got magnet. Release staff/prep spot.
        prep_staff.release(req_staff)
        
        # Move to Scan
        patient.state = 'Scanning'
        start_scan = env.now
        
        yield env.timeout(scan_dur)
        stats.magnet_busy_time += scan_dur
        stats.throughput += 1
        
        stats.event_log.append({
            'Start': start_scan, 'Finish': env.now, 
            'Resource': 'Magnet', 'State': 'Scanning'
        })
        
        magnet.release(req_magnet)
        
        patient.state = 'Done'
        
        # Bed Flip (Parallel - usually shorter, e.g. 1.5m)
        # Machine is blocked during flip? Yes.
        # But we released it? 
        # If we release it, someone else grabs it.
        # We must HOLD it or have a separate "Cleaner" seize it immediately.
        # Simpler: Don't release magnet until flip is done.
        # But for Parallel, prompt says "Scan -> Release".
        # And Bed Flip is 1.5 mins "Pit Crew".
        # Let's assume Flip is part of the Magnet Cycle.
        # Re-acquiring magnet for flip is risky (someone else might cut in).
        # So I will hold magnet during flip.
        
        # Correction: `req_magnet` was released above. I should move release to AFTER flip.
        # But "Parallel" logic means we want to minimize magnet time.
        # Ideally: Patient leaves -> Cleaner enters.
        # Current logic: Patient Scan -> Flip -> Release.
        # This keeps Magnet Busy (Yellow).
        
        # Let's Modify the parallel block to hold magnet for flip:
        # (This contradicts my code above where I released it).
        # I'll just change the logic in the main loop to match this.

def handle_patient_parallel(env, patient, magnet, prep_staff, stats, bed_flip_time):
    # Specialized function to avoid nested context issues
    
    # 1. Seize Prep Staff
    req_staff = prep_staff.request()
    yield req_staff
    
    patient.state = 'Prepping'
    
    # Prep Times
    screening_dur = get_triangular_sample(config.screening_time)
    change_dur = get_triangular_sample(config.change_time)
    needs_iv = (random.random() < config.prob_needs_IV)
    iv_dur = get_triangular_sample(config.iv_setup_time) if needs_iv else 0.0
    total_prep_time = screening_dur + change_dur + iv_dur
    
    yield env.timeout(total_prep_time)
    
    # 2. Wait for Magnet
    req_magnet = magnet.request()
    yield req_magnet
    
    # 3. Got Magnet -> Release Prep Staff
    prep_staff.release(req_staff)
    
    # 4. Scan
    patient.state = 'Scanning'
    scan_dur = get_normal_sample(config.scan_duration)
    start_scan = env.now
    yield env.timeout(scan_dur)
    stats.event_log.append({
        'Start': start_scan, 'Finish': env.now, 
        'Resource': 'Magnet', 'State': 'Scanning'
    })
    
    stats.magnet_busy_time += scan_dur
    stats.throughput += 1
    patient.state = 'Done' # Patient leaves room
    
    # 5. Bed Flip (Parallel)
    start_flip = env.now
    yield env.timeout(bed_flip_time)
    stats.event_log.append({
        'Start': start_flip, 'Finish': env.now, 
        'Resource': 'Magnet', 'State': 'Changeover'
    })
    
    # 6. Release Magnet
    magnet.release(req_magnet)

def patient_generator(env, magnet, prep_staff, stats, parallel_prep, bed_flip_time, all_patients):
    p_id = 0
    while True:
        p_id += 1
        
        # Create Patient Object
        patient = Patient(p_id)
        all_patients.append(patient)
        
        # Noise
        arrival_offset = get_normal_sample(config.arrival_noise)
        
        # Launch Process
        if not parallel_prep:
            env.process(handle_patient(env, patient, magnet, prep_staff, stats, False, bed_flip_time))
        else:
            env.process(handle_patient_parallel(env, patient, magnet, prep_staff, stats, bed_flip_time))
            
        yield env.timeout(config.booking_slot)

def run_simulation(staff_count, bed_flip_time, parallel_flag):
    """
    Main entry point for App or Script.
    """
    env = simpy.Environment()
    
    # Resources
    magnet = simpy.Resource(env, capacity=1)
    # prompt: "Staff Count: Slider (3 to 6)".
    # If Parallel: Prep happens in Zone 2. Constraints: Prep Staff? 
    # If Serial: Prep happens in Magnet. Staff is effectively bound to Magnet? 
    # Let's use `prep_staff` as the resource for Zone 2. 
    # If Serial, maybe this resource is unused? 
    # Actually, in Serial, Techs are in the room.
    # Let's set capacity = staff_count.
    # In Parallel, we need Staff for Prep AND Staff for Scan?
    # Usually Scan takes 1-2 techs. Prep takes 1.
    # We can model `prep_staff` as the pool of available techs.
    # Scan consumes 1 tech + Magnet. Prep consumes 1 tech.
    # But my `handle_patient` logic above complicates this if I add more resource requests.
    # SIMPLIFICATION:
    # "Staff Count" -> Capacity of `prep_staff` resource (Parallel Limit).
    # Since Magnet is the bottleneck, Scan always claims 1 tech implicitly.
    # So `prep_staff` available for Zone 2 = Total Staff - 1 (for Scanner).
    # Let's do that: `prep_capacity = max(1, staff_count - 1)`
    
    prep_capacity = max(1, staff_count - 1)
    prep_staff = simpy.Resource(env, capacity=prep_capacity)
    
    stats = MRI_Stat_Tracker()
    all_patients = []
    animation_data = []
    
    # Processes
    env.process(patient_generator(env, magnet, prep_staff, stats, parallel_flag, bed_flip_time, all_patients))
    env.process(monitor_process(env, all_patients, animation_data))
    
    env.run(until=720) # 12 hours
    
    # Format Results
    df_anim = pd.DataFrame(animation_data)
    
    # Utilization
    scan_util = (stats.magnet_busy_time / 720) * 100
    
    return {
        "throughput": stats.throughput,
        "utilization": scan_util,
        "animation_df": df_anim,
        "gantt_log": stats.event_log
    }

if __name__ == "__main__":
    # Test run
    res = run_simulation(staff_count=4, bed_flip_time=5, parallel_flag=False)
    print(f"Serial Throughput: {res['throughput']}")
    
    res2 = run_simulation(staff_count=4, bed_flip_time=1.5, parallel_flag=True)
    print(f"Parallel Throughput: {res2['throughput']}")
