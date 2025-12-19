"""
Statistical Aggregator Module
=============================
Advanced data collection for batch/headless simulation.
"""

from src.analysis.tracker import SimStats

class MetricAggregator(SimStats):
    """
    Enhanced stats collector for batch runs.
    Tracks granular utilization for all resource types.
    """
    def __init__(self, warm_up_duration=None):
        super().__init__(warm_up_duration)
        
        # Enhanced Utilization Tracking (Occupied Minutes Accumulators)
        self.occupied_minutes = {
            'zone1': 0.0,
            'change_rooms': 0.0,
            'washrooms': 0.0,
            'waiting_room': 0.0,
            'room_311': 0.0,
            'prep_rooms': 0.0,
            'magnet_3t': 0.0,
            'magnet_15t': 0.0
        }
        
        # Idle Time Accumulators
        self.idle_minutes = {
            'magnet_3t': 0.0,
            'magnet_15t': 0.0
        }
        
        # Staff Metrics
        self.staff_break_minutes = {
            'porter': 0.0,
            'admin': 0.0,
            'backup': 0.0,
            'scan': 0.0
        }
        
        # Breakdown of Magnet Time (Value-Add vs Overhead)
        self.magnet_metrics = {
            'scan_value_added': 0.0, # Pure Green Time
            'scan_overhead': 0.0,    # Setup + Exit + Handover (Brown Time)
            'scan_gap': 0.0          # Unused gaps (Idle)
        }
        
        # Protocol Counters
        self.scan_counts = {} # "protocol_name" -> count
        
        # System Counts
        self.counts = {
            'outpatient': 0,
            'inpatient': 0,
            'late_arrival': 0,
            'no_show': 0
        }
        
        # Raw Patient Data (Dictionary for DataFrame conversion)
        self.patient_data = {} # pid -> dict

    def log_patient_finished(self, patient, now):
        """Override to capture detailed metrics."""
        super().log_patient_finished(patient, now)
        
        if now < self.warm_up_duration:
            return 

        if hasattr(patient, 'arrival_time'):
            total_time = now - patient.arrival_time
        else:
            total_time = 0

        # Capture detailed time metrics (from timers if available, else metrics)
        timers = getattr(patient, 'timers', {})
        metrics = getattr(patient, 'metrics', {})
        
        p_data = {
            'type': patient.patient_type,
            'total_time': total_time,
            'reg_time': timers.get('reg', metrics.get('reg', 0)),
            'change_time': metrics.get('change', 0), # Usually covered in 'reg' or 'prep' phase conceptually or separate? Keeping as metrics for now.
            'wash_time': metrics.get('washroom', 0),
            'prep_time': timers.get('prep', metrics.get('prep', 0)),
            'wait_time': timers.get('wait', metrics.get('wait', 0)),
            'scan_time': timers.get('scan', metrics.get('scan_room', 0)),
            'holding_time': timers.get('hold', metrics.get('holding_room', 0)),
            'protocol': getattr(patient, 'scan_protocol', 'Unknown'),
            'scan_duration': getattr(patient, 'scan_duration', 0.0), # Pure scan
            'overhead_duration': getattr(patient, 'overhead_duration', 0.0) # Local overhead
        }
        self.patient_data[patient.p_id] = p_data
        
        # Update Protocol Counts
        proto = p_data['protocol']
        self.scan_counts[proto] = self.scan_counts.get(proto, 0) + 1
        
        # Update counts
        if patient.patient_type == 'inpatient':
            self.counts['inpatient'] += 1
        else:
            self.counts['outpatient'] += 1
            
        if getattr(patient, 'is_late', False):
            self.counts['late_arrival'] += 1

    def log_magnet_metric(self, m_id, metric_type, duration):
        super().log_magnet_metric(m_id, metric_type, duration)
        # We handle no-show separately in counts if needed, but SimStats does it well.
        if metric_type == 'noshow':
            self.counts['no_show'] += 1
            
        # Granular tracking for Utilization Paradox
        if metric_type == 'scan':
            self.magnet_metrics['scan_value_added'] += duration
        elif metric_type in ['setup', 'exit', 'flip', 'handover']:
             self.magnet_metrics['scan_overhead'] += duration

    def capture_resource_usage(self, resource_map):
        """Called periodically to snapshot utilization."""
        # This is expected to be called by ResourceMonitor
        # resource_map: mapping of internal key to simpy.Resource
        pass 
