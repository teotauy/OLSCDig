#!/usr/bin/env python3
"""
Wrapper script that logs when other scripts are run.
Usage: python3 run_with_logging.py <script_name>
Example: python3 run_with_logging.py checkout.py
"""

import sys
import subprocess
import os
from datetime import datetime

def log_script_run(script_name):
    """Log that a script was run."""
    log_file = f"last_run_{script_name.replace('.py', '')}.log"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(log_file, 'w') as f:
        f.write(timestamp)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_with_logging.py <script_name>")
        print("Example: python3 run_with_logging.py checkout.py")
        sys.exit(1)
    
    script_name = sys.argv[1]
    
    # Log the run
    log_script_run(script_name)
    
    # Run the actual script
    try:
        result = subprocess.run([sys.executable, script_name], check=True)
        print(f"✅ {script_name} completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(f"❌ Script not found: {script_name}")
        sys.exit(1)

if __name__ == "__main__":
    main()
