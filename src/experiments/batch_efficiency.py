import os
import shutil
import pandas as pd
import multiprocessing
import time
import matplotlib.pyplot as plt
import seaborn as sns
import contextlib
import sys
import random
import simpy
from src.core.headless import HeadlessSimulation, HeadlessPatient
from src.core.workflows.patient import PatientWorkflow
import src.config as config
from src.core.staff_controller import StaffManager
from src.analysis.stats import MetricAggregator

# --- MOCK SIMULATION WITH CUSTOM GENERATOR ---

class BatchEfficiencySim(HeadlessSimulation):
    def __init__(self, settings, seed):
        super().__init__(settings, seed)
        self.patient_sequence = settings.get('patient_sequence', [])
        
    def run(self):
        random.seed(self.seed)
        env = simpy.Environment()
        
        # Mocks
        renderer = type('MockRenderer', (), {'add_sprite': lambda *a: None, 'remove_sprite': lambda *a: None, 'cleanup': lambda *a: None, 'render_frame': lambda *a: True})()
        stats = MetricAggregator()
        
        # 3. Resources (Mirroring headless.py)
        # We need to capture m3t and m15t explicitly for monitoring
        m3t_res = simpy.PriorityResource(env, capacity=1)
        m3t_res.last_exam_type = None
        m15t_res = simpy.PriorityResource(env, capacity=1)
        m15t_res.last_exam_type = None
        
        resources = {
            'porter': simpy.PriorityResource(env, capacity=config.STAFF_COUNT['porter']),
            'backup_techs': simpy.PriorityResource(env, capacity=config.STAFF_COUNT['backup_tech']),
            'scan_techs': simpy.Resource(env, capacity=config.STAFF_COUNT['scan_tech']),
            'admin_ta': simpy.Resource(env, capacity=config.STAFF_COUNT['admin']),
            'magnet_access': simpy.PriorityResource(env, capacity=2),
            'magnet_pool': simpy.Store(env, capacity=2),
            'change_1': simpy.Resource(env, capacity=1),
            'change_2': simpy.Resource(env, capacity=1),
            'change_3': simpy.Resource(env, capacity=1),
            'prep_1': simpy.Resource(env, capacity=1),
            'prep_2': simpy.Resource(env, capacity=1),
            'magnet_3t_res': m3t_res, 
            'magnet_15t_res': m15t_res,
            'waiting_room_left': {}, # Mocking pos manager buffer
            'waiting_room_right': {},
            'gap_mode_active': False
        }
        
        # Helper Mocks
        resources['get_free_change_room'] = lambda: ('change_1')
        resources['get_free_change_room_with_index'] = lambda: ('change_1', 0)
        resources['get_free_washroom'] = lambda: ('washroom_1')
        resources['get_free_washroom_with_index'] = lambda: ('washroom_1', 0)
        
        # Populate Magnet Pool
        m3t_config = {'id': '3T', 'resource': m3t_res, 'loc': config.MAGNET_3T_LOC, 'name': 'magnet_3t', 'visual_state': 'clean'}
        m15t_config = {'id': '1.5T', 'resource': m15t_res, 'loc': config.MAGNET_15T_LOC, 'name': 'magnet_15t', 'visual_state': 'clean'}
        resources['magnet_pool'].put(m3t_config)
        resources['magnet_pool'].put(m15t_config)
        
        # Staff
        from src.core.headless import HeadlessStaff
        staff_dict = {
            'porter': HeadlessStaff('porter', 0, 0),
            'admin': HeadlessStaff('admin', 0, 0),
            'backup': [HeadlessStaff('backup', 0, 0) for _ in range(2)],
            'scan': [HeadlessStaff('scan', 0, 0) for _ in range(2)]
        }
        
        staff_mgr = StaffManager(env, staff_dict, resources, with_breaks=False)
        staff_mgr.manage_breaks()
        
        # --- CUSTOM GENERATOR ---
        def controlled_generator():
            count = 0
            for proto in self.patient_sequence:
                count += 1
                p = HeadlessPatient(count, 0, 0)
                p.clinical_init_done = True
                p.scan_protocol = proto
                p.scan_params = config.SCAN_PROTOCOLS[proto]
                p.needs_iv = False # Simplify for throughput test
                p.is_difficult_iv = False
                p.is_inpatient = False
                p.arrival_time = env.now
                
                # Mock Workflow
                workflow = PatientWorkflow(env, resources, stats, renderer, staff_dict)
                env.process(workflow.run(p))
                
                # Arrival Interval (Fast injection to stress setup times)
                yield env.timeout(5) 
                
        env.process(controlled_generator())
        
        # Run until all processed
        while stats.patients_completed < len(self.patient_sequence):
            env.step()
            if env.now > 10000: break # Safety
            
        return {
            'duration': env.now,
            'patients_completed': stats.patients_completed,
            'magnet_gap': stats.magnet_metrics.get('scan_gap', 0) # Placeholder if needed
        }

# --- EXPERIMENT RUNNER ---

@contextlib.contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout

def _worker_task(seed_and_settings):
    seed, settings = seed_and_settings
    with suppress_stdout():
        sim = BatchEfficiencySim(settings, seed)
        return sim.run()

def run_experiment():
    SIMS = 100
    print(f"=== BATCH EFFICIENCY EXPERIMENT (N={SIMS}) ===")
    
    # Define Sequences (N=10 patients)
    # High Entropy: Mixed
    scenarios = []
    
    mixed_seq = ['brain_routine', 'prostate', 'spine', 'cardiac', 'abdomen_body'] * 2
    random.shuffle(mixed_seq) # One consistent random mix for definition? Or random per run?
    # Let's fix it for Scenario A to be "Mixed"
    mixed_seq = ['brain_routine', 'prostate', 'spine', 'cardiac', 'abdomen_body', 'brain_routine', 'prostate', 'spine', 'cardiac', 'abdomen_body']
    
    batched_seq = ['prostate'] * 10 # The "Prostate Block"
    
    print(f"Scenario A (Mixed): {mixed_seq}")
    print(f"Scenario B (Batched): {batched_seq}")
    
    task_configs = [
        {'label': 'Mixed (High Entropy)', 'sequence': mixed_seq},
        {'label': 'Batched (Low Entropy)', 'sequence': batched_seq}
    ]
    
    results = []
    
    for tc in task_configs:
        print(f"\nRunning {tc['label']}...")
        tasks = []
        base_seed = int(time.time())
        for i in range(SIMS):
            settings = {'patient_sequence': tc['sequence']}
            tasks.append((base_seed + i, settings))
            
        with multiprocessing.Pool() as pool:
            batch_res = pool.map(_worker_task, tasks)
            
        durations = [r['duration'] for r in batch_res]
        avg_dur = sum(durations) / len(durations)
        print(f"  Avg Makespan: {avg_dur:.1f} minutes")
        
        for d in durations:
            results.append({'Scenario': tc['label'], 'Makespan': d})
            
    # Analysis
    df = pd.DataFrame(results)
    
    # Calculate Savings
    avg_mixed = df[df['Scenario'] == 'Mixed (High Entropy)']['Makespan'].mean()
    avg_batch = df[df['Scenario'] == 'Batched (Low Entropy)']['Makespan'].mean()
    savings = avg_mixed - avg_batch
    slots_gained = savings / 30 # Approx 30 min slot
    
    print("\n=== RESULTS ===")
    print(f"Mixed Avg:   {avg_mixed:.1f} min")
    print(f"Batched Avg: {avg_batch:.1f} min")
    print(f"Savings:     {savings:.1f} min")
    print(f"Efficiency:  +{slots_gained:.1f} virtual slots created per 10 patients")
    
    # Plot
    plt.figure(figsize=(10, 7))
    sns.set_context("talk")
    sns.set_style("whitegrid")
    
    # Update labels for clarity in plot data? Or just use what is in DF.
    # The DF has 'Batched (Low Entropy)'. Let's map it or use as is but annotate.
    # Actually, let's just use the labels defined in task_configs above, but maybe rename them there?
    # No, risky to change logic mid-flight if I don't re-run simulation? 
    # Re-running simulation is fine, it's fast.
    # I will stick to existing DF labels but customize plot.
    
    ax = sns.barplot(x='Scenario', y='Makespan', data=df, errorbar='sd', palette=['#e74c3c', '#2ecc71'])
    
    plt.title("Impact of Sequence Dependent Setup\n(Batching Similar Protocols: Prostate Exams)", pad=20, fontsize=16, fontweight='bold')
    plt.ylabel("Total Time to Process 10 Patients (Min)", labelpad=15)
    plt.xlabel("Scheduling Strategy", labelpad=15)
    plt.ylim(0, 350) # Give headroom for text
    
    # Add Bar Labels
    for container in ax.containers:
        ax.bar_label(container, fmt='%.1f min', padding=3, fontweight='bold')
        
    # Add Efficiency Arrow/Text
    # Coordinates: midpoint between bars, somewhat high
    mid_x = 0.5
    start_y = avg_mixed
    end_y = avg_batch
    
    # Draw arrow from Mixed down to Batched level
    # Actually, simpler to just put text box describing savings.
    
    text_str = (f"Savings: {savings:.1f} min\n"
                f"(~{slots_gained:.1f} Extra Slots)\n"
                f"via Setup Optimization")
                
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax.text(0.5, 300, text_str, fontsize=12, verticalalignment='top', horizontalalignment='center', bbox=props)
    
    plt.tight_layout()
    
    outfile = "results/plots/batching_efficiency.png"
    os.makedirs('results/plots', exist_ok=True)
    plt.savefig(outfile)
    print(f"Saved Plot: {outfile}")

if __name__ == "__main__":
    run_experiment()
