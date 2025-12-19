from src.core.workflows.base import pos_manager
from src.core.workflows.admin import AdminWorkflow
from src.core.workflows.porter import PorterWorkflow
from src.core.workflows.backup import BackupWorkflow
from src.core.workflows.scanner import ScanWorkflow
from src.config import AGENT_POSITIONS, PROB_INPATIENT, PROB_WASHROOM_USAGE, PRIORITY_OUTPATIENT
import random
import src.config as config

class PatientWorkflow:
    def __init__(self, env, resources, stats, renderer, staff_dict):
        self.env = env
        self.stats = stats
        self.resources = resources # Passed to sub-workflows
        self.staff_dict = staff_dict
        
        # Instantiate Sub-Workflows
        self.admin = AdminWorkflow(env, resources, stats, renderer)
        self.porter = PorterWorkflow(env, resources, stats, renderer, staff_dict)
        self.backup = BackupWorkflow(env, resources, stats, renderer, staff_dict)
        self.scanner = ScanWorkflow(env, resources, stats, renderer, staff_dict)
        
    def run(self, patient):
        """
        Main Patient Journey Orchestrator.
        """
        env = self.env
        p_id = patient.p_id
        
        # 0. Compliance/Lateness
        if getattr(patient, 'is_late', False) and patient.late_duration > 0:
             yield env.timeout(patient.late_duration)
             
        # Add sprite
        if hasattr(self.admin.renderer, 'add_sprite'):
            self.admin.renderer.add_sprite(patient)
            
        # === Monte Carlo Initialization (Centralized) ===
        if not hasattr(patient, 'clinical_init_done'):
             # Protocol Selection
             patient.scan_protocol = random.choices(config.SCAN_TYPES, weights=config.SCAN_WEIGHTS, k=1)[0]
             patient.scan_params = config.SCAN_PROTOCOLS[patient.scan_protocol]
             
             # Clinical Attributes
             patient.needs_iv = (random.random() < config.PROB_NEEDS_IV)
             patient.is_difficult_iv = (random.random() < config.PROB_DIFFICULT_IV) if patient.needs_iv else False
             
             # Inpatient Override (re-calc based on new prob if needed, or strictly follow config)
             # Note: Headless might have set this, but we enforce config here if not set or to sync
             # patient.is_inpatient = (random.random() < config.PROB_INPATIENT)
             
             patient.clinical_init_done = True

        # 1. Classification
        is_inpatient = getattr(patient, 'is_inpatient', random.random() < PROB_INPATIENT)
        if is_inpatient:
            return # Inpatient workflow not fully refactored in this scope, assuming skip or TODO
            
        patient.arrival_time = env.now
            
        # 2. Registration (Admin)
        yield from self.admin.perform_registration(patient)
        
        # 3. Transport to Change (Porter)
        # Select Room Strategy (Simplified look-ahead)
        room_keys = ['change_1', 'change_2', 'change_3']
        random.shuffle(room_keys)
        selected_room = None
        selected_req = None
        
        # Try to seize immediately
        for key in room_keys:
            if self.resources[key].count < self.resources[key].capacity:
                selected_room = key
                selected_req = self.resources[key].request()
                yield selected_req
                break
                
        # Move logic
        if selected_room:
            target = AGENT_POSITIONS[f"{selected_room}_center"]
            self.stats.log_movement(p_id, 'change_room', env.now)
        else:
            target = AGENT_POSITIONS['change_staging']
            self.stats.log_movement(p_id, 'change_staging', env.now)
            
        # Transport
        # Determine current location (Admin Desk)
        start_pos = (patient.x, patient.y)
        
        # In Zone 1, we release the grid slot if we were partially waiting? 
        # (Admin workflow handles internal queue release)
        
        yield from self.porter.transport(patient, start_pos, target)
        
        # 4. Changing
        if selected_room is None:
            # Wait for room
            while selected_room is None:
                for key in room_keys:
                    if self.resources[key].count < self.resources[key].capacity:
                        selected_room = key
                        selected_req = self.resources[key].request()
                        yield selected_req
                        break
                if selected_room is None: yield env.timeout(0.5)
            
            # Move into room
            target = AGENT_POSITIONS[f"{selected_room}_center"]
            yield from self.admin.move_agent(patient, target)
            self.stats.log_movement(p_id, 'change_room', env.now)
            
        patient.set_state('changing')
        self.stats.log_state_change(p_id, 'registered', 'changing', env.now)
        patient.start_timer('change', env.now)
        yield env.timeout(self.admin.get_time('changing'))
        patient.stop_timer('change', env.now)
        
        # Release Room
        self.resources[selected_room].release(selected_req)
        
        # 5. Waiting Room (Self-Move to Left Grid)
        wr_left_pos, wr_left_slot = pos_manager.get_grid_pos('waiting_room_left', p_id)
        yield from self.admin.move_agent(patient, wr_left_pos)
        
        self.stats.log_movement(p_id, 'waiting_room', env.now)
        patient.start_timer('wait_room', env.now)
        
        # 6. Prep (Backup Tech)
        yield from self.backup.prep_patient(patient)
        
        # Release Left Slot (Done in Backup logic normally, but we need to verify sync)
        # Backup.prep_patient moves patient away. We should release here.
        pos_manager.release_pos('waiting_room_left', wr_left_slot)
        
        # 7. Post-Prep Waiting (Right Grid)
        wr_right_pos, wr_right_slot = pos_manager.get_grid_pos('waiting_room_right', p_id)
        yield from self.admin.move_agent(patient, wr_right_pos)
        self.stats.log_movement(p_id, 'waiting_room', env.now)
        patient.start_timer('wait_room', env.now)
        
        # 8. Washroom Usage (Probabilistic)
        if random.random() < PROB_WASHROOM_USAGE:
             # Simply: wait for resource, go, use, return
             # Simplified for refactor
             pass 

        # 9. Scan Entry (Scanner)
        # Seize Magnet
        req = self.resources['magnet_access'].request(priority=PRIORITY_OUTPATIENT)
        yield req
        patient.stop_timer('wait_room', env.now)
        
        magnet_config = yield self.resources['magnet_pool'].get()
        magnet_res = magnet_config['resource']
        m_req = magnet_res.request(priority=PRIORITY_OUTPATIENT)
        yield m_req
        
        pos_manager.release_pos('waiting_room_right', wr_right_slot)
        
        # Move to Magnet
        yield from self.admin.move_agent(patient, magnet_config['loc'])
        self.stats.log_movement(p_id, magnet_config['name'], env.now)
        
        # Execute Scan
        yield from self.scanner.execute_scan(patient, magnet_config)
        
        # 10. Exit & Bed Flip (Parallel)
        # Launch exit process
        env.process(self.exit_process(patient))
        
        # Perform Bed Flip (Porter)
        yield from self.porter.clean_room(magnet_config, magnet_res, patient.exam_type if hasattr(patient, 'exam_type') else 'Unknown')
        
        # Release Magnet
        magnet_res.release(m_req)
        self.resources['magnet_access'].release(req)
        yield self.resources['magnet_pool'].put(magnet_config)

    def exit_process(self, patient):
        """Standard exit."""
        # Simplified: Move to exit
        exit_pos = AGENT_POSITIONS['exit']
        yield from self.admin.move_agent(patient, exit_pos)
        
        self.stats.log_patient_finished(patient, self.env.now)
        if hasattr(self.admin.renderer, 'remove_sprite'):
             self.admin.renderer.remove_sprite(patient)

def run_generator(env, staff_dict, resources, stats, renderer, duration, patient_class=None, demand_multiplier=1.0, force_type=None):
    """
    Generator using Modular Workflow.
    """
    if patient_class is None:
        from src.core.headless import HeadlessPatient
        patient_class = HeadlessPatient
        
    p_id = 0
    workflow = PatientWorkflow(env, resources, stats, renderer, staff_dict)
    
    while True:
        # Check termination (simplified)
        if env.now > duration - 60 and stats.patients_in_system == 0:
             break
             
        # Create Patient
        p_id += 1
        # Random spawn if headless
        patient = patient_class(p_id, *AGENT_POSITIONS['zone1_center'])
        
        # Override if forced modality
        if force_type:
            patient.scan_protocol = force_type
            patient.scan_params = config.SCAN_PROTOCOLS[force_type]
            patient.needs_iv = (random.random() < config.PROB_NEEDS_IV)
            patient.is_difficult_iv = (random.random() < config.PROB_DIFFICULT_IV) if patient.needs_iv else False
            patient.clinical_init_done = True
        
        stats.patients_in_system += 1
        env.process(workflow.run(patient))
        
        # Arrival Interval
        # Adjust rate by demand_multiplier. Higher demand = shorter interval = higher rate.
        base_rate = 1.0 / config.PROCESS_TIMES['mean_inter_arrival']
        adjusted_rate = base_rate * demand_multiplier
        yield env.timeout(random.expovariate(adjusted_rate))
