#!/usr/bin/env python3
"""
MRI Digital Twin - Main Entry Point
====================================
Modular architecture demonstration of MRI department workflow simulation.

Usage:
    python main.py [--duration MINUTES] [--patients COUNT]

Example:
    python main.py --duration 120 --patients 10
"""

import argparse
from src.core.engine import run_simulation

def main():
    """Main entry point with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description='MRI Digital Twin - Agent-Based Simulation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                              # Default: 120 min, 10 patients
  python main.py --duration 60 --patients 5   # Quick test
  python main.py --duration 480 --patients 20 # Full day simulation
        """
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=120,
        help='Simulation duration in minutes (default: 120)'
    )
    
    parser.add_argument(
        '--patients',
        type=int,
        default=10,
        help='Maximum number of patients to simulate (default: 10)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='results',
        help='Output directory for reports (default: results)'
    )
    
    args = parser.parse_args()
    
    # Run simulation
    results = run_simulation(
        duration_minutes=args.duration,
        max_patients=args.patients,
        output_dir=args.output
    )
    
    # Print final summary
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    utilization = results['utilization']
    print(f"Throughput:           {utilization['throughput']} patients")
    print(f"Magnet Busy (Value):  {utilization['magnet_busy_pct']}%")
    print(f"Magnet Idle:          {utilization['magnet_idle_pct']}%")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit(main())
