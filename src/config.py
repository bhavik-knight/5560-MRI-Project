
import random
import statistics

class MRIConfig:
    """
    Configuration and Data Distributions for MRI Efficiency Simulation.
    Source: Empirical data from Sheets 1-4.
    Time Units: Minutes.
    """
    
    # --- System Parameters ---
    ARRIVAL_SCHEDULE = 30  # Minutes (Sheet 2)
    BED_FLIP_TIME_CURRENT = 5.0  # Minutes
    BED_FLIP_TIME_FUTURE = 1.0   # Minutes (Pit Crew)
    
    # --- Probabilities (Sheet 1) ---
    PROB_NEEDS_IV = 0.33
    PROB_DIFFICULT_IV = 0.01

    @staticmethod
    def get_screening_time():
        """Triangular Distribution (Sheet 4). returns minutes."""
        # Source: (125, 191, 309) seconds
        return random.triangular(125/60, 309/60, 191/60)

    @staticmethod
    def get_change_time():
        """Triangular Distribution (Sheet 4). returns minutes."""
        # Source: (92, 190, 347) seconds
        return random.triangular(92/60, 347/60, 190/60)

    @staticmethod
    def get_iv_setup_time():
        """Triangular Distribution (Sheet 4). returns minutes."""
        # Source: (92, 153, 245) seconds
        return random.triangular(92/60, 245/60, 153/60)

    @staticmethod
    def get_scan_duration():
        """Normal Distribution (Sheet 2 - Prostate). returns minutes."""
        # Mean 22.0, Std 5.0
        val = random.gauss(22.0, 5.0)
        return max(0, val)

    @staticmethod
    def get_arrival_delay():
        """Normal Noise for arrival. returns minutes."""
        # Assumed noise (0, 10) from previous prompt, sticking to it or default?
        # Prompt doesn't explicitly specify distribution for "arrival_schedule", just "30 mins".
        # But simulation needs noise usually. 
        # "System: arrival_schedule (30 mins)". 
        # I'll add a helper for noise if needed, or just keep it simple.
        # Let's keep the noise generator from before as a utility if needed, 
        # but for now the class just holds the specific definitions requested.
        return random.gauss(0, 10) 

if __name__ == "__main__":
    print("--- MRIConfig Data Verification ---")
    print(f"Screening Sample: {MRIConfig.get_screening_time():.2f} min")
    print(f"Change Sample:    {MRIConfig.get_change_time():.2f} min")
    print(f"IV Setup Sample:  {MRIConfig.get_iv_setup_time():.2f} min")
    print(f"Scan Sample:      {MRIConfig.get_scan_duration():.2f} min")
    print(f"Prob Needs IV:    {MRIConfig.PROB_NEEDS_IV}")
    print(f"Bed Flip Future:  {MRIConfig.BED_FLIP_TIME_FUTURE} min")
