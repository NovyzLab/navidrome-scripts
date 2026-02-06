"""
Watcher script - periodically runs the main download orchestrator.
Simplified from the old multi-script approach.
"""
import time
import subprocess
import sys
import os
import random

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CHECK_INTERVAL_SECONDS

# Project root for finding main.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, 'main.py')


def run_main_script():
    """Execute the main orchestrator script."""
    try:
        print("Running main download orchestrator...")
        result = subprocess.run(
            [sys.executable, MAIN_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=PROJECT_ROOT
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.returncode == 0:
            print("✓ Cycle completed successfully")
            return True
        else:
            print(f"✗ Cycle completed with exit code {result.returncode}")
            return False
            
    except FileNotFoundError:
        print(f"Error: main.py not found at {MAIN_SCRIPT}")
        return False
    except Exception as e:
        print(f"Error running main script: {e}")
        return False


def main():
    """Continuously monitors and runs the download orchestrator."""
    print("=" * 60)
    print("Music Download Watcher")
    print("=" * 60)
    print(f"\nChecking every {CHECK_INTERVAL_SECONDS} seconds.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n--- [{timestamp}] Starting download cycle ---\n")
            
            run_main_script()
            
            # Add some randomness to avoid predictable patterns
            sleep_time = CHECK_INTERVAL_SECONDS + random.uniform(-3, 3)
            print(f"\nWaiting {sleep_time:.0f} seconds until next cycle...")
            time.sleep(max(10, sleep_time))  # Minimum 10 seconds

    except KeyboardInterrupt:
        print("\n\nWatcher stopped. Goodbye!")


if __name__ == "__main__":
    main()
