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
            'holding_time': timers.get('hold', metrics.get('holding_room', 0))
        }
        self.patient_data[patient.p_id] = p_data
        self.patient_data[patient.p_id] = p_data
        
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

    def capture_resource_usage(self, resource_map):
        """Called periodically to snapshot utilization."""
        # This is expected to be called by ResourceMonitor
        # resource_map: mapping of internal key to simpy.Resource
        pass 
