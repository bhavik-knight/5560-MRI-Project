"""
Headless Simulation Kernel
==========================
High-performance logic kernel for batch processing.
Replicates engine.py exactly but without PyGame/Sprite overhead.
"""

import simpy
import random
import src.config as config
from src.core.workflow import patient_generator
from src.core.staff_controller import StaffManager
from src.analysis.stats import MetricAggregator

class HeadlessEntity:
    """Mock base class for Staff/Patients without PyGame Sprite overhead."""
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
        self.target_x = x
        self.target_y = y
        self.p_id = 0 # For patients
        
    def move_to(self, x, y=None):
        """Instant teleport for headless efficiency."""
        if y is None and isinstance(x, (tuple, list)):
            x, y = x
        self.target_x = x
        self.target_y = y
        self.x = x
        self.y = y
        
    def is_at_target(self):
        """Always True for headless mode (instant movement)."""
        return True
        
    def return_home(self):
        """Return to home position."""
        if hasattr(self, 'home_x') and hasattr(self, 'home_y'):
            self.move_to(self.home_x, self.home_y)
            
    def cover_position(self, x, y=None):
        """Move to cover a position."""
        self.move_to(x, y)
        
    def go_to_break(self):
        """Move to break room."""
        # Using config break room location
        bx, by = config.AGENT_POSITIONS['break_room_center']
        self.move_to(bx, by)
    
    def set_state(self, state):
        """Mock visual state change."""
        pass
        
    def start_timer(self, timer_name, now):
        """Mock timer start for patients."""
        if not hasattr(self, 'metrics'):
             self.metrics = {}
        pass # metrics often handled in stats object anyway, but workflow calls this

    def stop_timer(self, timer_name, now):
        """Mock timer stop."""
        pass

class HeadlessStaff(HeadlessEntity):
    def __init__(self, role, x, y):
        super().__init__(x, y)
        self.role = role
        self.home_x = x
        self.home_y = y
        self.busy = False
        self.last_used_time = 0

class HeadlessPatient(HeadlessEntity):
    def __init__(self, p_id, x, y):
        super().__init__(x, y)
        self.p_id = p_id
        self.metrics = {} # Stores completed durations
        self.timers = { # Accumulators
            'reg': 0.0, 'wait': 0.0, 'prep': 0.0, 'scan': 0.0, 'hold': 0.0
        }
        self.state_start_time = 0.0
        self.is_late = False
        self.late_duration = 0
        self.has_iv = False
        self.is_difficult = False  # Restored for tracker compatibility
        
        # Monte Carlo Attributes
        self.is_inpatient = (random.random() < config.PROB_INPATIENT)
        self.patient_type = 'inpatient' if self.is_inpatient else 'outpatient'
        
        self.needs_iv = (random.random() < config.PROB_IV_NEEDED)
        # Use config.PROB_DIFFICULT_IV
        self.is_difficult_iv = (random.random() < config.PROB_DIFFICULT_IV) if self.needs_iv else False
        
        # Protocol Selection
        # Randomly select a protocol
        proto_name = random.choice(list(config.SCAN_PROTOCOLS.keys()))
        self.scan_protocol = proto_name
        self.scan_params = config.SCAN_PROTOCOLS[proto_name]
        
    def start_timer(self, timer_name, now):
        """Start tracking duration for a specific phase."""
        self.state_start_time = now
        
    def stop_timer(self, timer_name, now):
        """Stop tracking and accumulate duration."""
        duration = now - self.state_start_time
        if timer_name == 'admin': timer_name = 'reg' # normalize key
        if timer_name == 'waiting_room' or timer_name == 'wait_room': timer_name = 'wait'
        if timer_name == 'scan_room': timer_name = 'scan'
        if timer_name == 'holding_room': timer_name = 'hold'
        
        # Accumulate in self.timers
        if timer_name in self.timers:
            self.timers[timer_name] += duration
        
        # Also store in flat metrics for workflow compat
        self.metrics[timer_name] = self.metrics.get(timer_name, 0.0) + duration
        return duration

class ResourceMonitor:
    """Monitors resource usage over time."""
    def __init__(self, env, resources, stats):
        self.env = env
        self.resources = resources
        self.stats = stats
        self.occupied_minutes = {k: 0.0 for k in resources.keys()}
        # Specifically split magnets if they are in 'magnet_pool'
        self.occupied_minutes['magnet_3t'] = 0.0
        self.occupied_minutes['magnet_15t'] = 0.0
        self.occupied_minutes['waiting_room'] = 0.0 # Explicitly init
        self.occupied_minutes['prep_rooms'] = 0.0
        
        # Import global pos_manager for accurate waiting room tracking
        from src.core.workflow import pos_manager
        self.pos_manager = pos_manager
        
    def run(self):
        while True:
            # Sample every minute
            yield self.env.timeout(1.0)
            
            # Simple discrete integration: 1 minute * count
            
            # Waiting Room: Read from PositionManager (Global source of truth for location)
            wr_count = len(self.pos_manager.occupancy.get('waiting_room_left', {})) + \
                       len(self.pos_manager.occupancy.get('waiting_room_right', {}))
            self.stats.occupied_minutes['waiting_room'] += wr_count
            
            # Change Rooms
            cr_count = 0
            for k in ['change_1', 'change_2', 'change_3']:
                if k in self.resources: cr_count += self.resources[k].count
            self.stats.occupied_minutes['change_rooms'] += cr_count
            
            # Washrooms
            wr_count = 0
            for k in ['washroom_1', 'washroom_2']:
                if k in self.resources: wr_count += self.resources[k].count
            self.stats.occupied_minutes['washrooms'] += wr_count
            
            # Prep: Use Backup Tech count as proxy since workflow doesn't seize prep rooms
            # This generally represents patients being prepped or escorted
            if 'backup_techs' in self.resources:
                 self.stats.occupied_minutes['prep_rooms'] += self.resources['backup_techs'].count
            
            # Holding / Room 311
            if 'room_311' in self.resources:
                self.stats.occupied_minutes['room_311'] += self.resources['room_311'].count
                
            # Magnets Utilization
            if 'magnet_3t_res' in self.resources:
                cnt = self.resources['magnet_3t_res'].count
                self.stats.occupied_minutes['magnet_3t'] += cnt
                if cnt == 0: self.stats.idle_minutes['magnet_3t'] += 1.0

            if 'magnet_15t_res' in self.resources:
                cnt = self.resources['magnet_15t_res'].count
                self.stats.occupied_minutes['magnet_15t'] += cnt
                if cnt == 0: self.stats.idle_minutes['magnet_15t'] += 1.0

class HeadlessSimulation:
    def __init__(self, settings, seed):
        self.settings = settings
        self.seed = seed
        
    def run(self):
        random.seed(self.seed)
        
        env = simpy.Environment()
        
        # 1. Mock Renderer
        renderer = type('MockRenderer', (), {
            'add_sprite': lambda *a: None, 
            'remove_sprite': lambda *a: None, 
            'cleanup': lambda *a: None, 
            'render_frame': lambda *a: True
        })()
        
        # 2. Stats
        stats = MetricAggregator()
        
        # 3. Resources (Mirroring engine.py)
        # We need to capture m3t and m15t explicitly for monitoring
        m3t_res = simpy.PriorityResource(env, capacity=1)
        m3t_res.last_exam_type = None
        m15t_res = simpy.PriorityResource(env, capacity=1)
        m15t_res.last_exam_type = None
        
        resources = {
            'porter': simpy.PriorityResource(env, capacity=config.STAFF_COUNT['porter']),
            'backup_techs': simpy.Resource(env, capacity=config.STAFF_COUNT['backup_tech']),
            'scan_techs': simpy.Resource(env, capacity=config.STAFF_COUNT['scan_tech']),
            'admin_ta': simpy.Resource(env, capacity=config.STAFF_COUNT['admin']),
            'magnet_access': simpy.PriorityResource(env, capacity=2),
            'magnet_pool': simpy.Store(env, capacity=2),
            'change_1': simpy.Resource(env, capacity=1),
            'change_2': simpy.Resource(env, capacity=1),
            'change_3': simpy.Resource(env, capacity=1),
            'washroom_1': simpy.Resource(env, capacity=1),
            'washroom_2': simpy.Resource(env, capacity=1),
            'holding_room': simpy.Resource(env, capacity=1),
            'room_311': simpy.Resource(env, capacity=getattr(config, 'ROOM_311_CAPACITY', 2)),
            'prep_1': simpy.Resource(env, capacity=1), # Explicitly named for tracking if needed
            'prep_2': simpy.Resource(env, capacity=1),
            # Add magnet resources for raw access if needed
            'magnet_3t_res': m3t_res, 
            'magnet_15t_res': m15t_res
        }
        
        # Helpers (same as engine.py)
        def get_free_change_room_with_index():
            room_keys = ['change_1', 'change_2', 'change_3']
            random.shuffle(room_keys)
            for idx, key in enumerate(room_keys):
                if resources[key].count < resources[key].capacity:
                    return key, idx
            return None, None
        
        def get_free_washroom_with_index():
            room_keys = ['washroom_1', 'washroom_2']
            random.shuffle(room_keys)
            for idx, key in enumerate(room_keys):
                if resources[key].count < resources[key].capacity:
                    return key, idx
            return None, None
            
        resources['get_free_change_room'] = lambda: get_free_change_room_with_index()[0]
        resources['get_free_washroom'] = lambda: get_free_washroom_with_index()[0]
        resources['get_free_change_room_with_index'] = get_free_change_room_with_index
        resources['get_free_washroom_with_index'] = get_free_washroom_with_index
        
        # Populate Magnet Pool
        # 3T
        m3t_config = {
            'id': '3T',
            'resource': m3t_res,
            'loc': config.MAGNET_3T_LOC,
            'name': 'magnet_3t',
            'visual_state': 'clean'
        }
        # 1.5T
        m15t_config = {
            'id': '1.5T',
            'resource': m15t_res,
            'loc': config.MAGNET_15T_LOC,
            'name': 'magnet_15t',
            'visual_state': 'clean'
        }
        resources['magnet_pool'].put(m3t_config)
        resources['magnet_pool'].put(m15t_config)
        
        # 4. Initialize Staff (Headless Objects)
        staff_dict = {
            'porter': HeadlessStaff('porter', *config.AGENT_POSITIONS['porter_home']),
            'admin': HeadlessStaff('admin', *config.AGENT_POSITIONS['admin_home']),
            'backup': [HeadlessStaff('backup', *config.AGENT_POSITIONS['backup_staging']) for _ in range(config.STAFF_COUNT['backup_tech'])],
            'scan': []
        }
        # Scan Techs specific locs
        scan_locs = [config.AGENT_POSITIONS['scan_staging_3t'], config.AGENT_POSITIONS['scan_staging_15t']]
        for i in range(config.STAFF_COUNT['scan_tech']):
            loc = scan_locs[i] if i < len(scan_locs) else scan_locs[0]
            staff_dict['scan'].append(HeadlessStaff('scan', *loc))
            
        # 5. Staff Manager
        staff_mgr = StaffManager(env, staff_dict, resources)
        staff_mgr.manage_breaks()
        
        # 6. Monitor
        monitor = ResourceMonitor(env, resources, stats)
        env.process(monitor.run())
        
        # 7. Generator
        duration = self.settings.get('duration', config.DEFAULT_DURATION)
        env.process(patient_generator(env, staff_dict, resources, stats, renderer, duration, patient_class=HeadlessPatient))
        
        # 8. Run
        env.run(until=duration)
        
        # 9. Overtime (Clear System)
        # Safety limit for overtime 
        overtime_limit = duration + 300 
        while stats.patients_in_system > 0 and env.now < overtime_limit:
             env.run(until=env.now + 1)
             
        # 10. Compile Results
        results = {
            'duration': env.now,
            'patients_completed': stats.patients_completed,
            'patients_in_system': stats.patients_in_system,
            'late_arrivals': stats.counts['late_arrival'],
            'no_shows': stats.counts['no_show'],
            'occupied_minutes': stats.occupied_minutes,
            'counts': stats.counts,
            'patient_data': stats.patient_data,
            'magnet_3t_occupied': stats.occupied_minutes.get('magnet_3t', 0),
            'magnet_15t_occupied': stats.occupied_minutes.get('magnet_15t', 0),
            'magnet_3t_idle': stats.idle_minutes.get('magnet_3t', 0),
            'magnet_15t_idle': stats.idle_minutes.get('magnet_15t', 0),
            'magnet_metrics': stats.magnet_metrics,
            'scan_counts': stats.scan_counts
        }
        return results
