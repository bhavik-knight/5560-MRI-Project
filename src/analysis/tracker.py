"""
Tracker Module - Simulation Statistics Collection
==================================================
Records patient movements, state changes, and resource utilization
without cluttering the simulation loop.

Includes warm-up period handling to remove empty-system bias.
"""

from datetime import datetime
import src.config as config
from src.config import WARM_UP_DURATION

class PatientMetrics:
    """Individual patient performance data."""
    def __init__(self, p_id, p_type, arrival_time):
        self.id = p_id
        self.type = p_type
        self.arrival_time = arrival_time
        self.has_iv = False
        self.is_difficult = False
        self.durations = {
            'admin': 0.0,
            'change': 0.0,
            'washroom': 0.0,
            'prep': 0.0,
            'wait_room': 0.0,
            'scan_room': 0.0,
            'holding_room': 0.0,
            'bed_flip': 0.0
        }
        self.total_time_in_system = 0.0

class MagnetMetrics:
    """Magnet-specific throughput and utilization data."""
    def __init__(self, m_id):
        self.id = m_id
        self.patients_served = 0
        self.total_scan_time = 0.0     # Green Time (Value Added)
        self.total_setup_time = 0.0    # Yellow Time (Necessary Non-Value)
        self.total_flip_time = 0.0     # Yellow Time (Necessary Non-Value)
        self.total_exit_time = 0.0
        self.total_idle_time = 0.0
        self.last_event_time = 0.0

class SimStats:
    """
    Observer class for tracking simulation statistics.
    Records the 'Utilization Paradox' data - distinguishing between
    busy time (value-added scanning) vs occupied time (prep + scan).
    
    Excludes warm-up period from statistics to prevent empty-system bias.
    """
    
    def __init__(self, warm_up_duration=None):
        """
        Initialize statistics tracking.
        
        Args:
            warm_up_duration: Minutes to exclude from stats (default: from config)
        """
        self.warm_up_duration = warm_up_duration if warm_up_duration is not None else WARM_UP_DURATION
        """Initialize statistics tracking."""
        # Patient movement log
        self.patient_log = []
        
        # State change log
        self.state_changes = []
        
        # Resource utilization tracking
        self.magnet_busy_time = 0.0      # Time actually scanning (value-added)
        self.magnet_occupied_time = 0.0  # Time occupied (prep + scan in serial)
        
        # Comprehensive Analytics (User Request - Step 2)
        self.finished_patients = []
        self.magnets = {
            '3T': MagnetMetrics('3T'),
            '1.5T': MagnetMetrics('1.5T')
        }
        self.late_arrivals = 0
        self.critical_transfers = 0
        
        # Magnet state tracking (legacy support, but better used via MagnetMetrics)
        self._magnet_start_time = None
        self._magnet_state = 'idle'
        
        # Patient tracking
        self.patients_arrived = 0
        self.patients_completed = 0
        self.patients_in_system = 0
        
        # Queue tracking
        self.waiting_room_log = []
        
        # Smart Gatekeeper Status
        self.generator_active = True
        self.est_clearing_time = 0.0

        # Event Counter
        self.counts = {}
        
        # Headless Monitor Support
        self.occupied_minutes = {}
        self.idle_minutes = { 'magnet_3t': 0.0, 'magnet_15t': 0.0 }

        
    def log_movement(self, patient_id, zone, timestamp):
        """
        Record patient movement to a new zone.
        Only logs movements after warm-up period.
        
        Args:
            patient_id: Unique patient identifier
            zone: Zone name (e.g., 'zone1', 'change_1', 'magnet_3t')
            timestamp: Simulation time in minutes
        """
        # Skip logging during warm-up period
        if timestamp < self.warm_up_duration:
            return
            
        self.patient_log.append({
            'patient_id': patient_id,
            'zone': zone,
            'timestamp': timestamp - self.warm_up_duration,  # Adjust timestamp
            'event_type': 'movement'
        })
    
    def log_state_change(self, patient_id, old_state, new_state, timestamp):
        """
        Record patient state transition.
        Only logs state changes after warm-up period.
        
        Args:
            patient_id: Unique patient identifier
            old_state: Previous state ('arriving', 'changing', 'prepped', 'scanning')
            new_state: New state
            timestamp: Simulation time in minutes
        """
        # Always track system population (even during warm-up)
        # Always track system population (even during warm-up)
        if new_state == 'arriving':
            self.patients_arrived += 1
            self.patients_in_system += 1
        elif new_state == 'exited':
            # Decrement when patient explicitly exits the system
            self.patients_in_system -= 1
            if self.patients_in_system < 0:
                self.patients_in_system = 0 # Safety floor

        
        # Skip logging state changes during warm-up period
        if timestamp < self.warm_up_duration:
            return
            
        self.state_changes.append({
            'patient_id': patient_id,
            'old_state': old_state,
            'new_state': new_state,
            'timestamp': timestamp - self.warm_up_duration,  # Adjust timestamp
            'event_type': 'state_change'
        })
    
    def log_patient_finished(self, patient_sprite, env_now):
        """Record all metrics for a patient exiting the system."""
        metrics = PatientMetrics(
            patient_sprite.p_id, 
            patient_sprite.patient_type,
            patient_sprite.arrival_time
        )
        metrics.has_iv = patient_sprite.has_iv
        metrics.is_difficult = patient_sprite.is_difficult
        metrics.durations.update(patient_sprite.metrics)
        metrics.total_time_in_system = env_now - patient_sprite.arrival_time
        
        self.finished_patients.append(metrics)
        self.patients_completed += 1

    def log_magnet_metric(self, m_id, category, duration, now=None):
        """Record magnet-specific performance (Value Added vs Non-Value Added)."""
        if m_id in self.magnets:
            magnet = self.magnets[m_id]
            if category == 'scan':
                magnet.total_scan_time += duration
                magnet.patients_served += 1
            elif category == 'setup':
                magnet.total_setup_time += duration
            elif category == 'flip':
                magnet.total_flip_time += duration
            elif category == 'exit':
                magnet.total_exit_time += duration

    def log_completion(self, patient_id, magnet_id):
        """Legacy support - replaced by log_patient_finished."""
        pass

    
    def log_magnet_start(self, timestamp, is_scanning=False):
        """
        Record when magnet becomes occupied.
        
        Args:
            timestamp: Simulation time in minutes
            is_scanning: True if starting scan, False if starting prep
        """
        self._magnet_start_time = timestamp
        self._magnet_state = 'scanning' if is_scanning else 'prep'
    
    def log_magnet_end(self, timestamp):
        """
        Record when magnet becomes idle.
        
        Args:
            timestamp: Simulation time in minutes
        """
        if self._magnet_start_time is not None:
            duration = timestamp - self._magnet_start_time
            
            # Add to occupied time (total time magnet was in use)
            self.magnet_occupied_time += duration
            
            # Add to busy time only if it was actual scanning
            if self._magnet_state == 'scanning':
                self.magnet_busy_time += duration
            
            self._magnet_start_time = None
            self._magnet_state = 'idle'
    
    def log_waiting_room(self, patient_id, timestamp, action='enter'):
        """
        Record patient entering/leaving waiting room buffer.
        
        Args:
            patient_id: Unique patient identifier
            timestamp: Simulation time in minutes
            action: 'enter' or 'exit'
        """
        self.waiting_room_log.append({
            'patient_id': patient_id,
            'timestamp': timestamp,
            'action': action
        })
    
    def calculate_utilization(self, total_sim_time):
        """
        Calculate resource utilization metrics.
        
        Args:
            total_sim_time: Total simulation duration in minutes
        
        Returns:
            dict: Utilization metrics including the 'Utilization Paradox'
        """
        if total_sim_time == 0:
            return {
                'magnet_busy_pct': 0.0,
                'magnet_occupied_pct': 0.0,
                'magnet_idle_pct': 100.0,
                'throughput': 0,
                'avg_patients_in_system': 0.0
            }
        
        # Calculate percentages
        busy_pct = (self.magnet_busy_time / total_sim_time) * 100
        occupied_pct = (self.magnet_occupied_time / total_sim_time) * 100
        idle_pct = 100 - occupied_pct
        
        # The "Utilization Paradox":
        # In Serial workflow: occupied_pct is high (looks good) but busy_pct is low (bad)
        # In Parallel workflow: occupied_pct may be lower but busy_pct is higher (good)
        
        return {
            'magnet_busy_pct': round(busy_pct, 2),           # Value-added time
            'magnet_occupied_pct': round(occupied_pct, 2),   # Total occupied time
            'magnet_idle_pct': round(idle_pct, 2),           # True idle time
            'throughput': self.patients_completed,
            'patients_in_system': self.patients_in_system,
            'total_arrivals': self.patients_arrived,
            'scans_3t': self.magnets['3T'].patients_served,
            'scans_15t': self.magnets['1.5T'].patients_served,
        }

    
    def get_summary_stats(self, total_sim_time):
        """
        Get comprehensive summary statistics.
        
        Args:
            total_sim_time: Total simulation duration in minutes
        
        Returns:
            dict: Complete statistics summary
        """
        utilization = self.calculate_utilization(total_sim_time)
        
        wait_times = [p.durations.get('wait_room', 0) for p in self.finished_patients]
        avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0
        
        return {
            **utilization,
            'avg_wait_time': round(avg_wait, 2),
            'max_wait_time': round(max(wait_times), 2) if wait_times else 0,
            'total_movements': len(self.patient_log),
            'total_state_changes': len(self.state_changes),
        }
