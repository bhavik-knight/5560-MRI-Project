"""
Staff Controller Module
=======================
Manages staff break schedules and dynamic coverage logic (Human Factors).
Moved from engine.py for modularity.
"""

import simpy
import src.config as config

class StaffManager:
    """Manages staff break schedules and dynamic coverage logic."""
    def __init__(self, env, staff_dict, resources):
        self.env = env
        self.staff_dict = staff_dict
        self.resources = resources
        
        # Coverage Flags [Source: Human Factors Layer]
        self.porter_covering_admin = False
        self.scan_coverage_status = {} # tech_idx -> bool
        self.staff_on_break = {} # staff_id -> True
        
        # Share flags with resources for workflow access
        resources['staff_mgr'] = self
        
        # Break Room Capacity (Enforce strict limit: 1 person at a time)
        self.break_slot = simpy.Resource(env, capacity=1)
        
    def manage_breaks(self):
        """Orchestrates staggered breaks for all staff based on config."""
        schedule = config.BREAK_CONFIG['schedule'] # [30, 15, 30, 15]
        
        # Collect all individuals
        individuals = []
        # Porter (idx 0)
        individuals.append(('porter', 0, self.staff_dict['porter']))
        # Admin (idx 0)
        individuals.append(('admin', 0, self.staff_dict['admin']))
        # Backup Techs
        for i, tech in enumerate(self.staff_dict['backup']):
            individuals.append(('backup', i, tech))
        # Scan Techs
        for i, tech in enumerate(self.staff_dict['scan']):
            individuals.append(('scan', i, tech))
            
        # Start processes for each staff
        for role, idx, staff in individuals:
            self.env.process(self.staff_break_cycle(role, idx, staff, schedule))

    def staff_break_cycle(self, role, idx, staff, schedule):
        """Individual staff break logic including coverage transitions."""
        # Initial stagger to prevent simultaneous breaks in same role
        # Admin starts early, techs middle, porter spread
        start_delays = {
            'admin': 30,
            'backup': 60,
            'scan': 90,
            'porter': 120
        }
        yield self.env.timeout(start_delays.get(role, 60) + (idx * 20))
        
        for break_duration in schedule:
            # --- START BREAK REQUEST (Queue if break room full) ---
            with self.break_slot.request() as break_req:
                yield break_req
                
                staff_id = f"{role}_{idx}"
                self.staff_on_break[staff_id] = True
                
                # Coverage Transitions
                coverage_req = None
                backup_seizure_req = None
                
                if role == 'admin':
                    self.porter_covering_admin = True
                    # Porter must physically move to desk and stay there
                    # We seize porter resource so they can't do other tasks
                    coverage_req = self.resources['porter'].request(priority=-1) # Extreme high priority
                    yield coverage_req
                    self.staff_dict['porter'].cover_position(config.AGENT_POSITIONS['admin_home'])
                elif role == 'scan':
                    self.scan_coverage_status[idx] = True
                    
                    # 1. Summon Backup Tech
                    backup_tech = self.staff_dict['backup'][idx % len(self.staff_dict['backup'])]
                    
                    # Seize & Lock immediately so they don't take other tasks while walking
                    backup_seizure_req = self.resources['backup_techs'].request()
                    yield backup_seizure_req
                    backup_tech.busy = True 
                    
                    # 2. Backup moves to EXACT Scan Tech Station (Hot Seat)
                    backup_tech.cover_position(staff.home_x, staff.home_y)
                    if not config.HEADLESS:
                        print(f"[{self.env.now:.1f}] HANDSHAKE START: Backup {idx} moving to Station for Scan Tech {idx}")
                    
                    # 3. HANDSHAKE: Scan tech WAITS for Backup to arrive
                    while not backup_tech.is_at_target():
                        yield self.env.timeout(0.5)
                        
                    # 4. HANDOVER DELAY (User Request: 2 seconds)
                    yield self.env.timeout(2)
                    if not config.HEADLESS:
                        print(f"[{self.env.now:.1f}] HANDSHAKE COMPLETE: Scan Tech {idx} leaving for break.")
                    
                    # Now Backup is "in command" - Scan Tech free to leave
                    
                elif role == 'backup':
                    # Reduced prep capacity - seize a resource unit
                    backup_seizure_req = self.resources['backup_techs'].request()
                    yield backup_seizure_req
                    
                staff.go_to_break()
                yield self.env.timeout(break_duration)
                
                # --- END BREAK ---
                self.staff_on_break[staff_id] = False
                
                # Scan tech returns to ORIGINAL STATION first
                staff.return_home()
                
                # Wait for primary staff to physically return (Visual Handoff)
                while not staff.is_at_target():
                    yield self.env.timeout(0.5)
                
                # Revert Coverage
                if role == 'admin':
                    self.porter_covering_admin = False
                    if coverage_req:
                        self.resources['porter'].release(coverage_req)
                    self.staff_dict['porter'].return_home()
                elif role == 'scan':
                    # HANDOVER DELAY (User Request: 2 seconds)
                    yield self.env.timeout(2)
                    
                    self.scan_coverage_status[idx] = False
                    backup_tech = self.staff_dict['backup'][idx % len(self.staff_dict['backup'])]
                    backup_tech.return_home()
                    backup_tech.busy = False # UNLOCK: Free to do other tasks
                    if backup_seizure_req:
                        self.resources['backup_techs'].release(backup_seizure_req)
                elif role == 'backup':
                    if backup_seizure_req:
                        self.resources['backup_techs'].release(backup_seizure_req)
                
            # Wait for next block (e.g., 2.5 hours between breaks)
            yield self.env.timeout(150)
