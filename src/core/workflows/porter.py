from src.core.workflows.base import BaseWorkflow
from src.config import AGENT_POSITIONS

class PorterWorkflow(BaseWorkflow):
    def __init__(self, env, resources, stats, renderer, staff_dict):
        super().__init__(env, resources, stats, renderer)
        self.staff_dict = staff_dict
        
    def transport(self, patient, start_pos, end_target, end_target_key=None):
        """
        Escort logic: Porter moves to patient, then both move to target.
        """
        env = self.env
        porter = self.staff_dict['porter']
        
        with self.resources['porter'].request(priority=1) as req:
            yield req
            
            porter.busy = True
            
            # 1. Porter comes to patient
            yield from self.move_agent(porter, (patient.x, patient.y))
            
            # 2. Escort to target
            # Note: Parallel movement needs 'simpy.AllOf' or distinct processes if we want precise sync
            # For simplicity, we move patient and porter sequentially in small steps or just "teleport" logic wrapper
            # But BaseWorkflow.move_agent is a generator.
            # Implementing simple "move together":
            
            target_pos = end_target
            if isinstance(end_target, str):
                 target_pos = AGENT_POSITIONS.get(end_target, (0,0))
                 
            # Start moving both (visual approximation) - ideally we'd link them
            # Here we just block until arrival
            porter.move_to(*target_pos)
            patient.move_to(*target_pos)
            
            # Wait for patient (as the primary agent)
            while True:
                dist = ((patient.x - target_pos[0])**2 + (patient.y - target_pos[1])**2)**0.5
                if dist < 5: break
                yield env.timeout(0.01)
                
            porter.busy = False
            porter.return_home()
            
    def clean_room(self, magnet_config, magnet_res, patient_prev_exam):
        """
        Bed Flip / Cleaning Logic.
        """
        env = self.env
        stats = self.stats
        m_id = magnet_config['id']
        
        with self.resources['porter'].request(priority=0) as req:
            yield req
            
            porter = self.staff_dict['porter']
            porter.busy = True
            
            # Move to room
            yield from self.move_agent(porter, magnet_config['loc'])
            
            # Logic: SMED (Fast Flip) vs Slow Flip
            last_exam = magnet_res.last_exam_type
            current_exam = patient_prev_exam 
            
            is_same_exam = (last_exam == patient_prev_exam)
            
            # Empirical Distributions [Source 26]
            if is_same_exam:
                # FAST FLIP (Tech Assisted)
                duration = self.get_time('bed_flip_fast')
            else:
                # SLOW FLIP (Porter Solo)
                duration = self.get_time('bed_flip_slow') 
                
            # Log and Wait
            magnet_config['visual_state'] = 'dirty' # Brown
            yield env.timeout(duration)
            stats.log_magnet_metric(m_id, 'flip', duration, env.now)
            magnet_config['visual_state'] = 'clean'
            
            # Update state
            magnet_res.last_exam_type = patient_prev_exam
            
            porter.busy = False
            porter.return_home()
