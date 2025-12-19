import src.config as config

class BaseWorkflow:
    def __init__(self, env, resources, stats, renderer):
        self.env = env
        self.resources = resources
        self.stats = stats
        self.renderer = renderer
        
    def log(self, patient, message):
        """Standardized logging."""
        # For debug or console output if needed
        # print(f"[{self.env.now:.1f}] Patient {patient.p_id}: {message}")
        pass

    def record_stage(self, patient, stage_name, duration):
        """Wrap stats recording."""
        if hasattr(patient, 'timers'):
            # It's an accumulator, usually we stop the timer here
            # But if we are given a fixed duration, just log it?
            # Creating a unified interface might be tricky for start/stop vs duration.
            # Assuming 'duration' is passed, we log it.
            pass
        
    def move_agent(self, agent, target, threshold=5):
        """
        Move an agent to a target location.
        Handles both tuple (x, y) and config string keys if logical.
        """
        if isinstance(target, str):
            # Assume key in AGENT_POSITIONS
            target_pos = config.AGENT_POSITIONS.get(target, (0,0))
        else:
            target_pos = target
            
        agent.move_to(*target_pos)
        
        while True:
            dist = ((agent.x - target_pos[0])**2 + (agent.y - target_pos[1])**2)**0.5
            if dist < threshold:
                break
            yield self.env.timeout(0.01)
            
    def get_time(self, task_name):
        """Helper to sample process times."""
        import random
        from src.config import PROCESS_TIMES
        params = PROCESS_TIMES.get(task_name)
        if params is None: return 1.0
        if isinstance(params, (int, float)): return params
        return random.triangular(*params)
        
    def stat_log_event(self, p_id, event_name):
        """Log singular event."""
        # self.stats.log_event(p_id, event_name) # If stats supports it
        pass

from src.config import ROOM_COORDINATES

class PositionManager:
    """Manages available slots in waiting areas to prevent overlapping."""
    def __init__(self):
        # Dictionary to track occupied slots in each area/sub-area
        # Key: Area name, Value: List of (id, x, y)
        self.occupancy = {
            'zone1': {},
            'waiting_room_left': {},
            'waiting_room_right': {}
        }
        
    def get_grid_pos(self, area, p_id):
        """Calculate next available grid position for an area."""
        # Determine base room key
        if area.startswith('waiting_room'):
            room_key = 'waiting_room'
        else:
            room_key = area.split('_')[0]
            
        # Grid parameters
        start_x, start_y, width, height = ROOM_COORDINATES[room_key]
        
        # Override specific area boundaries based on user request
        if area == 'zone1':
            # Public room - left border
            base_x = 100
            base_y = start_y + 20
            max_y = start_y + height - 20
            spacing = 35
        elif area == 'waiting_room_left':
            # Waiting room - changed patients - left border
            base_x = start_x + 20
            base_y = start_y + 20
            max_y = start_y + height - 20
            spacing = 25
        elif area == 'waiting_room_right':
            # Waiting room - prepped patients - right border
            base_x = start_x + width - 20
            base_y = start_y + 20
            max_y = start_y + height - 20
            spacing = 25
            
        # Find first empty slot index
        occupied_indices = sorted(self.occupancy[area].keys())
        slot_idx = 0
        while slot_idx in occupied_indices:
            slot_idx += 1
            
        # Calculate x, y based on vertical-first grid
        column_capacity = max(1, (max_y - base_y) // spacing)
        col = slot_idx // column_capacity
        row = slot_idx % column_capacity
        
        if area == 'waiting_room_right':
            # Fill right-to-left
            x = base_x - (col * spacing)
        else:
            # Fill left-to-right
            x = base_x + (col * spacing)
            
        y = base_y + (row * spacing)
        
        # Save occupancy
        self.occupancy[area][slot_idx] = p_id
        return (x, y), slot_idx

    def release_pos(self, area, slot_idx):
        """Release a slot."""
        if slot_idx in self.occupancy[area]:
            self.occupancy[area].pop(slot_idx)

# Global Manager
pos_manager = PositionManager()
