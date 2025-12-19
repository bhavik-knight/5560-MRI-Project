from src.core.workflows.base import BaseWorkflow
from src.config import AGENT_POSITIONS
import random

class BackupWorkflow(BaseWorkflow):
    def __init__(self, env, resources, stats, renderer, staff_dict):
        super().__init__(env, resources, stats, renderer)
        self.staff_dict = staff_dict

    def prep_patient(self, patient):
        """
        Retrieves patient from Waiting Room, performs Prep/IV.
        """
        env = self.env
        p_id = patient.p_id
        
        # Request Backup Tech
        # Singles Line Logic: Check Mode + Simple Patient
        prio = 1 # Default Normal Priority
        
        # Check if Gap Mode Active (Magnet Idle > 5m)
        if self.resources.get('gap_mode_active', False):
            # Check if patient is "Simple"
            # Definition: No Difficult IV, Outpatient
            is_simple = (not getattr(patient, 'is_difficult_iv', False) and 
                         getattr(patient, 'patient_type', 'outpatient') == 'outpatient')
            
            if is_simple:
                prio = 0 # HIGH PRIORITY (Jump the line)
                # print(f"🚀 Singles Line Activated for Patient {p_id}")

        with self.resources['backup_techs'].request(priority=prio) as req:
            yield req
            
            # Select specific staff member (closest or round robin)
            techs = self.staff_dict['backup']
            tech = next((t for t in techs if not t.busy), techs[0])
            tech.busy = True
            
            # 1. Fetch from Waiting Room
            # Assuming patient is at 'waiting_room_left' based on flow
            yield from self.move_agent(tech, (patient.x, patient.y))
            
            # 2. Go to Prep & Recovery (Zone 2)
            # Use 'prep_1' or 'prep_2' via resource
            # We need to seize a prep room resource realistically?
            # Original code mostly used the tech handling prep.
            # But let's assume we move to prep area.
            prep_loc = (tech.home_x, tech.home_y) # Staging area or room
            
            yield from self.move_agent(patient, prep_loc)
            yield from self.move_agent(tech, prep_loc)
            
            self.stats.log_movement(p_id, 'prep_room', env.now)
            
            # 3. Clinical Work (IV & Interview)
            patient.start_timer('prep', env.now)
            
            # Clinical Attributes (Assigned in PatientWorkflow)
            if getattr(patient, 'needs_iv', False):
                patient.has_iv = True
                
                if getattr(patient, 'is_difficult_iv', False):
                    # Difficult IV
                    dur = self.get_time('iv_difficult')
                    # Verification Log
                    print(f"⚠️ Difficult IV for Patient {p_id} (Duration: {dur:.1f}m)")
                    self.stat_log_event(p_id, "Difficult IV") 
                else:
                    # Normal IV
                    dur = self.get_time('iv_prep')
                    
                yield env.timeout(dur)
            
            # Standard Screening/Interview
            yield env.timeout(self.get_time('screening'))
            
            patient.stop_timer('prep', env.now)
            patient.set_state('prepped')
            
            tech.busy = False
            tech.return_home()
