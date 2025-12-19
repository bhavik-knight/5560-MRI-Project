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
import os

# Suppress PyGame import message for clean batch output
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

def main():
    """Main entry point with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description='MRI Digital Twin - Agent-Based Simulation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                        # Default: 2 hour shift (120 min)
  python main.py --duration 480         # 8 hour shift
  python main.py --duration 720         # 12 hour shift
        """
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=None,  # Will use DEFAULT_DURATION from config
        help='Simulation duration in minutes (default: 120 = 2 hours)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='results',
        help='Output directory for reports (default: results)'
    )
    
    parser.add_argument(
        '--record',
        action='store_true',
        help='Record simulation to video file'
    )
    
    parser.add_argument(
        '--mkv',
        action='store_true',
        help='Use MKV format instead of MP4 (default: MP4)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        default='visual',
        choices=['visual', 'batch'],
        help='Simulation mode: visual (PyGame) or batch (Headless Monte Carlo)'
    )
    
    parser.add_argument(
        '--sims',
        type=int,
        default=1000,
        help='Number of simulations per epoch (Batch mode only)'
    )
    
    parser.add_argument(
        '--epochs',
        type=int,
        default=1,
        help='Number of epochs (Batch mode only)'
    )
    parser.add_argument(
        '--singles-line',
        action='store_true',
        help='Enable Singles Line logic (Short notice gap filling)'
    )
    
    parser.add_argument(
        '--demand',
        type=float,
        default=1.0,
        help='Demand multiplier (1.0 = 100%, 1.5 = 150%, etc.)'
    )
    
    parser.add_argument(
        '--force-type',
        type=str,
        default=None,
        help='Force all patients to a specific protocol execution (e.g., brain_routine)'
    )
    
    parser.add_argument(
        '--no-show-prob',
        type=float,
        default=None,
        help='Override global No-Show probability (0.0 - 1.0)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'batch':
        # --- BATCH HEADLESS MODE ---
        from src.batch_run import execute_batch
        # Note: execute_batch needs update if we want to support force_type there too
        # But strictly speaking user asked for main/engine update
        # We can pass it if we update batch_run, but let's stick to the prompt's explicit scope for main/engine.
        # But for correctness, passing it to execute_batch via **kwargs or explicit arg is better if batch mode is used.
        # However, the experiment script is `compare_modalities.py` which will likely instantiate HeadlessSimulation directly.
        # I will update execute_batch call here assuming I update batch_run quickly next, or just ignore for batch mode CLI usage if not strictly required.
        # Let's assumes execute_batch accepts kwargs or explicit. I'll stick to visual path update mostly unless I touch batch_run.
        # Wait, I can pass strict args.
        execute_batch(
            sims=args.sims, 
            epochs=args.epochs, 
            singles_line_mode=args.singles_line, 
            demand_multiplier=args.demand,
            force_type=args.force_type,
            no_show_prob=args.no_show_prob
        )
        return 0
        
    else:
        # --- VISUAL MODE ---
        from src.core.engine import run_simulation
        
        # Determine video format
        video_format = 'mkv' if args.mkv else 'mp4'
        
        # Run simulation
        results = run_simulation(
            duration=args.duration,
            output_dir=args.output,
            record=args.record,
            video_format=video_format,
            singles_line_mode=args.singles_line,
            demand_multiplier=args.demand,
            force_type=args.force_type,
            no_show_prob=args.no_show_prob
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
