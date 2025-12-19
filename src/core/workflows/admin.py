from src.core.workflows.base import BaseWorkflow
from src.config import AGENT_POSITIONS, PURPLE_REGISTERED
import random
import src.config as config

# Global queue state (moved from workflow.py)
ADMIN_QUEUE = []

def update_admin_queue():
    """Update positions of all patients waiting for Admin."""
    base_x, base_y = AGENT_POSITIONS['admin_home']
    queue_start_x = base_x + 50 
    spacing = 30
    
    for i, patient in enumerate(ADMIN_QUEUE):
        target_x = queue_start_x + (i * spacing)
        patient.move_to(target_x, base_y)

class AdminWorkflow(BaseWorkflow):
    def perform_registration(self, patient):
        """
        Manage the patient arrival, queueing, and registration process.
        """
        p_id = patient.p_id
        env = self.env
        
        # 1. Join Queue
        patient.set_state('arriving')
        self.stats.log_state_change(p_id, None, 'arriving', env.now)
        
        ADMIN_QUEUE.append(patient)
        update_admin_queue()
        
        # 2. Wait for Resource
        with self.resources['admin_ta'].request() as req:
            yield req
            
            # Leave Queue
            if patient in ADMIN_QUEUE:
                ADMIN_QUEUE.remove(patient)
                update_admin_queue()
                
            # Approach Desk
            admin_x, admin_y = AGENT_POSITIONS['admin_home']
            yield from self.move_agent(patient, (admin_x, admin_y + 25))
            
            # Wait for Admin/Covering Staff
            staff_mgr = self.resources.get('staff_mgr')
            # Determine who is serving (Admin or Covering Porter)
            is_covered = getattr(staff_mgr, 'porter_covering_admin', False) if staff_mgr else False
            staff_dict = getattr(staff_mgr, 'staff', {}) # Assuming we can access this or pass it
            
            # Note: access to staff objects is tricky if not in resources. 
            # In headless, staff_mgr holds them.
            # We might need to assume 'admin' resource implies service availability, 
            # but visual physical presence check was in original code.
            # For simplicity in refactor, we retain the resource wait as primarily blocking.
            
            # Registration Task
            patient.color = PURPLE_REGISTERED
            self.stats.log_state_change(p_id, 'arriving', 'registered', env.now)
            
            # Empirical Distribution [Source 14]
            patient.start_timer('admin', env.now)
            yield env.timeout(self.get_time('registration'))
            patient.stop_timer('admin', env.now)
            
            return True # Success
