
import simpy
import pandas as pd
import random
from src.config import MRIConfig
from src.resources import MRIResources
from src.entities import Patient

class MRISimulation:
    def __init__(self, simulation_hours=12, parallel_mode=False, staff_count=4, bed_flip_time=None):
        self.simulation_hours = simulation_hours
        self.parallel_mode = parallel_mode
        self.staff_count = staff_count
        self.bed_flip_override = bed_flip_time
        self.patient_logs = []
        self.spatial_logs = []
        self.active_patients = []
        
    def patient_generator(self, env, resources, config):
        """Generates patients based on configured schedule and noise."""
        p_id = 0
        while True:
            p_id += 1
            
            # Arrival Schedule
            inter_arrival = config.ARRIVAL_SCHEDULE # 30 mins
            noise = config.get_arrival_delay()
            
            yield env.timeout(inter_arrival)
            
            arrival_offset = max(0, noise) 
            actual_arrival_time = env.now + arrival_offset
            
            patient = Patient(p_id, actual_arrival_time)
            
            # We need a wrapper to handle the offset delay before process_flow starts
            env.process(self._handle_patient(env, patient, resources, config, arrival_offset))

    def _handle_patient(self, env, patient, resources, config, delay):
        if delay > 0:
            yield env.timeout(delay)
        
        # Add to active list for Monitoring
        self.active_patients.append(patient)
        
        yield from patient.process_flow(
            env, 
            resources, 
            config, 
            parallel_mode=self.parallel_mode,
            bed_flip_override=self.bed_flip_override,
            log_records=self.patient_logs
        )
        
        # Remove from active list? 
        # Or keep them if we want to track 'Exit' state for a bit?
        # Monitor logic handles 'Done'.
        pass

    def monitor_spatial_state(self, env):
        """
        Runs every 1 minute to snapshot patient locations.
        """
        while True:
            current_time = env.now
            
            for patient in self.active_patients:
                state = getattr(patient, 'state', 'Unknown')
                
                # Default mapping
                x, y = 0, 0
                
                if state == 'Arrived/Waiting':
                    # Zone 1
                    x = 0
                    y = random.uniform(0, 5)
                elif state in ['Prepping', 'Changed', 'IV Setup']:
                    # Zone 2 (Wait/Prep)
                    x = 1
                    y = random.uniform(0, 5)
                elif state == 'Scanning':
                    # Zone 4
                    x = 2
                    y = 2
                elif state == 'Done':
                    # Exit
                    x = 3
                    y = random.uniform(0, 5)
                
                self.spatial_logs.append({
                    'Minute': int(current_time),
                    'Patient_ID': patient.id,
                    'State': state,
                    'X': x,
                    'Y': y
                })
            
            yield env.timeout(1)

    def run(self):
        """
        Initializes and runs the simulation.
        Returns a dict containing patient logs and spatial dataframe.
        """
        env = simpy.Environment()
        
        # Instantiate Resources
        resources = MRIResources(env, self.staff_count)
        
        # Start Generator
        env.process(self.patient_generator(env, resources, MRIConfig))
        
        # Start Monitor
        env.process(self.monitor_spatial_state(env))
        
        # Run
        env.run(until=self.simulation_hours * 60)
        
        # Format Spatial Logs
        df_spatial = pd.DataFrame(self.spatial_logs)
        
        return {
            "patient_logs": self.patient_logs,
            "spatial_data": df_spatial
        }
