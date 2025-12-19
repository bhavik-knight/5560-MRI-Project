from src.core.workflows.base import BaseWorkflow
from src.config import PROCESS_TIMES
import random

class ScanWorkflow(BaseWorkflow):
    def __init__(self, env, resources, stats, renderer, staff_dict):
        super().__init__(env, resources, stats, renderer)
        self.staff_dict = staff_dict

    def execute_scan(self, patient, magnet_config):
        """
        Main Scanning Loop: Handover -> Setup -> Scan -> Exit.
        """
        env = self.env
        p_id = patient.p_id
        m_id = magnet_config['id']
        
        # 1. Tech Assignment
        # Logic: 3T -> Tech 0, 1.5T -> Tech 1 generic mapping
        tech_idx = 0 if m_id == '3T' else 1
        scan_techs = self.staff_dict['scan']
        scan_tech = scan_techs[tech_idx] if tech_idx < len(scan_techs) else scan_techs[0]
        
        scan_tech.busy = True
        
        # 2. Handover ("Hot Seat")
        # Overlap time between Backup (who brought patient) and Scan Tech
        handover_time = PROCESS_TIMES.get('handover', 2.0)
        yield env.timeout(handover_time)
        self.stats.log_magnet_metric(m_id, 'handover', handover_time, env.now)
        
        # 3. Patient State Update
        patient.set_state('scanning')
        self.stats.log_state_change(p_id, 'prepped', 'scanning', env.now)
        patient.start_timer('scan_room', env.now)
        
        magnet_config['visual_state'] = 'busy' # Green
        
        # 4. Setup
        setup_time = self.get_time('scan_setup')
        yield env.timeout(setup_time)
        self.stats.log_magnet_metric(m_id, 'setup', setup_time, env.now)
        
        # 5. Scan Execution (Value Added)
        self.stats.log_magnet_start(env.now, is_scanning=True)
        
        # Duration Logic
        scan_params = getattr(patient, 'scan_params', None)
        if scan_params and isinstance(scan_params, (tuple, list)):
            # Triangular Distribution (Min, Mode, Max)
            scan_time = random.triangular(*scan_params)
        elif scan_params and isinstance(scan_params, dict):
             # Fallback for dict format logic if mixed
             mean = scan_params.get('mean', 25.0)
             std = scan_params.get('std', 0.0)
             scan_time = max(5.0, random.gauss(mean, std))
        else:
            scan_time = self.get_time('scan_duration')
            
        yield env.timeout(scan_time)
        self.stats.log_magnet_metric(m_id, 'scan', scan_time, env.now)
        patient.scan_duration = scan_time # Store for stats
        
        # Verification Logging
        if not hasattr(self, '_log_count'): self._log_count = 0
        if self._log_count < 10: # Limit output
            print(f"Scanning ({getattr(patient, 'scan_protocol', 'unknown')}) for {scan_time:.1f} mins")
            self._log_count += 1
            
        self.stats.log_magnet_end(env.now)
        
        # 6. Exit / PACS Push
        exit_time = self.get_time('scan_exit')
        yield env.timeout(exit_time)
        self.stats.log_magnet_metric(m_id, 'exit', exit_time, env.now)
        
        patient.stop_timer('scan_room', env.now)
        magnet_config['visual_state'] = 'dirty'
        
        scan_tech.busy = False
