
import unittest
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.engine import MRISimulation

class TestMRISimulation(unittest.TestCase):
    def test_engine_runs_and_generates_patients(self):
        """
        Test that the engine runs for 1 hour and generates at least one patient record.
        """
        sim = MRISimulation(simulation_hours=2, parallel_mode=False)
        results = sim.run()
        logs = results['patient_logs']
        spatial_df = results['spatial_data']
        
        # Verify logs are not empty
        print(f"Debug: Generated {len(logs)} logs.")
        print(f"Debug: Generated {len(spatial_df)} spatial records.")
        
        self.assertTrue(len(logs) > 0, "Simulation should generate at least one patient log.")
        self.assertFalse(spatial_df.empty, "Spatial data should not be empty.")
        self.assertIn('X', spatial_df.columns)
        self.assertIn('Y', spatial_df.columns)
        
        # Verify log structure
        first_record = logs[0]
        self.assertIn('p_id', first_record)
        self.assertIn('arrival_time', first_record)
        self.assertEqual(first_record['scenario'], 'Serial')

if __name__ == '__main__':
    unittest.main()
