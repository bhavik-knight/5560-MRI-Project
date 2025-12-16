
import random

class Patient:
    def __init__(self, p_id, arrival_time):
        self.id = p_id
        self.arrival_time = arrival_time
        
    def process_flow(self, env, resources, config, parallel_mode=False, bed_flip_override=None, log_records=None):
        """
        Simulate the patient's journey through the MRI suite.
        """
        self.state = 'Arrived/Waiting'
        
        # calculate prep times once per patient
        screening_time = config.get_screening_time()
        change_time = config.get_change_time()
        
        needs_iv = (random.random() < config.PROB_NEEDS_IV)
        iv_time = config.get_iv_setup_time() if needs_iv else 0.0
        
        total_prep_time = screening_time + change_time + iv_time
        scan_time = config.get_scan_duration()
        
        # Decide Bed Flip Time logic
        if bed_flip_override is not None:
            bed_flip_time = bed_flip_override
        else:
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
                self.state = 'Prepping' # Zone 2/3 (inside room)
                prep_start = env.now
                if parallel_mode is False: # Occupying magnet room for prep
                    yield env.timeout(total_prep_time)
                
                # Scan
                self.state = 'Scanning'
                scan_start = env.now
                yield env.timeout(scan_time)
                
                # Turnaround / Flip
                # self.state = 'Flip'? or stay Scanning/Done? 
                # Prompt says "Done -> Exit". 
                # Keep Scanning during flip? Or 'Done'? 
                # Prompt mapping: "Done -> Exit". 
                # Let's switch to Done after scan?
                # But Flip happens *before* exit in Serial?
                # Usually patient leaves, then flip.
                # Let's set to Done.
                self.state = 'Done'
                yield env.timeout(bed_flip_time)
                
                exit_time = env.now

        else:
            # --- PARALLEL SCENARIO ---
            # Seize Prep_Room -> Prep -> Release Prep_Room -> Seize Magnet -> Scan -> Flip -> Release
            
            # 1. Seize Prep Room
            req_prep = resources.prep_rooms.request()
            yield req_prep
            
            # 2. Prep
            self.state = 'Prepping'
            prep_start = env.now
            yield env.timeout(total_prep_time)
            
            # 3. Release Prep Room
            resources.prep_rooms.release(req_prep)
            
            # Patient waiting for Magnet
            self.state = 'Arrived/Waiting' # Back to Zone 1? Or Zone 2 Waiting?
            # Prompt says: "Prepping/IV/Changed -> Zone 2". 
            # "Arrived/Waiting -> Zone 1".
            # Gowned waiting is technically Zone 2. 
            # Let's keep it as 'Prepping' or add 'Waiting Gowned'?
            # Using 'Prepping' keeps them in Zone 2 (X=1).
            # Using 'Arrived/Waiting' moves them to Zone 1 (X=0).
            # Logic: They are gowned, so Zone 2.
            # Let's keep state 'Prepping' or 'Changed'.
            self.state = 'Changed' 

            # 4. Seize Magnet
            req_mag = resources.magnet.request()
            yield req_mag
            
            # 5. Scan
            self.state = 'Scanning'
            scan_start = env.now
            yield env.timeout(scan_time)
            
            # 6. Turnaround / Flip
            self.state = 'Done'
            yield env.timeout(bed_flip_time)
            
            # 7. Release Magnet
            resources.magnet.release(req_mag)
            
            exit_time = env.now
        
        self.state = 'Done'

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
