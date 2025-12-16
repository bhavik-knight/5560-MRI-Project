
import simpy
from src.config import MRIConfig
from src.resources import MRIResources
from src.entities import Patient

class MRISimulation:
    def __init__(self, simulation_hours=12, parallel_mode=False, staff_count=4):
        self.simulation_hours = simulation_hours
        self.parallel_mode = parallel_mode
        self.staff_count = staff_count
        self.logs = []
        
    def patient_generator(self, env, resources, config):
        """Generates patients based on configured schedule and noise."""
        p_id = 0
        while True:
            p_id += 1
            
            # Arrival Schedule
            inter_arrival = config.ARRIVAL_SCHEDULE # 30 mins
            noise = config.get_arrival_delay()
            
            # Yield time for next scheduled slot
            # Note: simplified logic. A proper schedule creates slots. 
            # Here we just space them by 30 mins + noise? 
            # Prompt says "loop yielding Patient every 30 mins +/- noise".
            # The simplest way is to yield 30 mins, then spawn a process that waits (noise) before starting?
            # Or yield (30 + noise)? If noise is negative, we can't yield negative timeout.
            
            # Better Approach:
            # Yield 30 minutes.
            # Spawn a patient, but apply "lateness" (noise) to their *effective* arrival time processing?
            # Step 3 `process_flow` doesn't explicitly wait for arrival, it assumes it starts when called.
            # Let's yield max(0, 30 + noise) for spacing? 
            # Or better: yield 30. Then spawn `p.process_flow` with an initial `yield timeout(max(0, noise))`?
            # Let's do the latter.
            
            yield env.timeout(inter_arrival)
            
            # Determine actual arrival time (could be late)
            # Effectively, patient arrives NOW + Noise.
            # If Noise is negative (early), they arrived in the past? 
            # Simpy can't handle negative timeouts. 
            # Let's assume noise applies to the "Processing Start".
            
            arrival_offset = max(0, noise) 
            # Initial time is env.now (which is slot time). Patient arrives at env.now + offset.
            
            actual_arrival_time = env.now + arrival_offset
            patient = Patient(p_id, actual_arrival_time)
            
            # We need a wrapper to handle the offset delay before process_flow starts
            env.process(self._handle_patient(env, patient, resources, config, arrival_offset))

    def _handle_patient(self, env, patient, resources, config, delay):
        if delay > 0:
            yield env.timeout(delay)
        
        yield from patient.process_flow(
            env, 
            resources, 
            config, 
            parallel_mode=self.parallel_mode, 
            log_records=self.logs
        )

    def run(self):
        """
        Initializes and runs the simulation.
        Returns the logs.
        """
        env = simpy.Environment()
        
        # Instantiate Resources
        resources = MRIResources(env, self.staff_count)
        
        # Start Generator
        env.process(self.patient_generator(env, resources, MRIConfig))
        
        # Run
        env.run(until=self.simulation_hours * 60)
        
        return self.logs
