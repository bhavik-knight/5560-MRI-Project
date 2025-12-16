
import random

class Patient:
    def __init__(self, p_id, arrival_time):
        self.id = p_id
        self.arrival_time = arrival_time
        
    def process_flow(self, env, resources, config, parallel_mode=False, log_records=None):
        """
        Simulate the patient's journey through the MRI suite.
        """
        
        # calculate prep times once per patient
        screening_time = config.get_screening_time()
        change_time = config.get_change_time()
        
        needs_iv = (random.random() < config.PROB_NEEDS_IV)
        iv_time = config.get_iv_setup_time() if needs_iv else 0.0
        
        total_prep_time = screening_time + change_time + iv_time
        scan_time = config.get_scan_duration()
        
        # Decide Bed Flip Time logic
        bed_flip_time = config.BED_FLIP_TIME_FUTURE if parallel_mode else config.BED_FLIP_TIME_CURRENT

        # Timestamps for logging
        prep_start = None
        scan_start = None
        exit_time = None
        
        if not parallel_mode:
            # --- SERIAL SCENARIO ---
            # Seize Magnet -> Prep -> Scan -> Flip -> Release
            
            with resources.magnet.request() as req:
                yield req
                
                # Magnet Seized. Start Prep.
                prep_start = env.now
                if parallel_mode is False: # Occupying magnet room for prep
                    yield env.timeout(total_prep_time)
                
                # Scan
                scan_start = env.now
                yield env.timeout(scan_time)
                
                # Turnaround / Flip
                yield env.timeout(bed_flip_time)
                
                exit_time = env.now

        else:
            # --- PARALLEL SCENARIO ---
            # Seize Prep_Room -> Prep -> Release Prep_Room -> Seize Magnet -> Scan -> Flip -> Release
            
            # 1. Seize Prep Room
            req_prep = resources.prep_rooms.request()
            yield req_prep
            
            # 2. Prep
            prep_start = env.now
            # Consume Prep Staff if needed? prompt says "Seize Prep_Room". 
            # I will assume resources object handles specific constraints if complex, 
            # but prompt "Refactor Resources" defined prep_rooms.
            yield env.timeout(total_prep_time)
            
            # 3. Release Prep Room (Patient moves to Wait for Magnet)
            resources.prep_rooms.release(req_prep)
            
            # 4. Seize Magnet
            req_mag = resources.magnet.request()
            yield req_mag
            
            # 5. Scan
            scan_start = env.now
            yield env.timeout(scan_time)
            
            # 6. Turnaround / Flip
            yield env.timeout(bed_flip_time)
            
            # 7. Release Magnet (Context Exit handles this if using 'with', 
            # but here we used explicit request/release for prep logic gap)
            resources.magnet.release(req_mag)
            
            exit_time = env.now

        # Logging
        if log_records is not None:
            log_records.append({
                'p_id': self.id,
                'arrival_time': self.arrival_time,
                'prep_start': prep_start,
                'scan_start': scan_start,
                'exit_time': exit_time,
                'scenario': 'Parallel' if parallel_mode else 'Serial'
            })
