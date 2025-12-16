
import simpy

class MRIResources:
    def __init__(self, env, staff_count):
        self.env = env
        
        # --- Physical Resources ---
        self.magnet = simpy.Resource(env, capacity=1)
        
        # Source 10: "3 patients max in Zone 2" (Wait + Prep)
        # Assuming Prep Rooms are the constraint for "Prepping": 
        # Source 5: "2 prep rooms".
        # Let's set capacity=2 for specific Prep Rooms, or 3 for Zone 2 limit?
        # Prompt says: "prep_rooms (Capacity=2 or 3)".
        # I'll use 2 Prep Rooms as the hard constraint for "Prepping".
        self.prep_rooms = simpy.Resource(env, capacity=2)
        
        # --- Staff Resources ---
        # Logic to split `staff_count` (Techs + Porter)
        # Dedicated Porter = 1
        num_porters = 1
        
        # Remaining for Techs
        techs_available = max(1, staff_count - num_porters)
        
        # Scan Tech (Critical) - Needs to govern the Magnet
        # Usually 1 Scan Tech per Magnet.
        num_scan_techs = 1
        
        # Backup Techs (Float)
        num_backup_techs = max(0, techs_available - num_scan_techs)
        
        # Create Resources
        self.scan_tech = simpy.PriorityResource(env, capacity=num_scan_techs)
        self.backup_tech = simpy.PriorityResource(env, capacity=num_backup_techs) if num_backup_techs > 0 else None
        
        # Fallback: If 0 backup techs, maybe Scan Tech does it all? 
        # Simulation logic needs to handle `if backup_tech is None`.
        # OR we combine them? 
        # For this class, we just define them.
        
        self.porter = simpy.Resource(env, capacity=num_porters)
        
        # Metrics
        self.magnet_utilization_log = []

    def monitor_utilization(self):
        """
        Process to track magnet utilization over time.
        Records (time, usage_count) every minute.
        """
        while True:
            # Record current usage (0 or 1)
            usage = self.magnet.count
            self.magnet_utilization_log.append({
                'Minute': self.env.now,
                'Magnet_Occupied': usage
            })
            yield self.env.timeout(1)
