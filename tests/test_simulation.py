
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
        logs = sim.run()
        
        # Verify logs are not empty
        print(f"Debug: Generated {len(logs)} logs.")
        self.assertTrue(len(logs) > 0, "Simulation should generate at least one patient log.")
        
        # Verify log structure
        first_record = logs[0]
        self.assertIn('p_id', first_record)
        self.assertIn('arrival_time', first_record)
        self.assertEqual(first_record['scenario'], 'Serial')

if __name__ == '__main__':
    unittest.main()
