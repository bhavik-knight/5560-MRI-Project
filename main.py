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
  python main.py                        # Default: 12 hour shift (720 min)
  python main.py --duration 120         # 2 hour test
  python main.py --duration 480         # 8 hour shift
        """
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=None,  # Will use DEFAULT_DURATION from config
        help='Simulation duration in minutes (default: 720 = 12 hours)'
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
        duration=args.duration,
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
