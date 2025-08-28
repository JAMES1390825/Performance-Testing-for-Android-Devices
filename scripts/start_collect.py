import os
import subprocess
import sys
from datetime import datetime

# Define project directory dynamically
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)

VENV_PATH = os.path.join(PROJECT_DIR, ".venv")
PYTHON_EXECUTABLE = os.path.join(VENV_PATH, "bin", "python")

# Set application package for specific app monitoring
APP_PACKAGE = os.getenv("APP_PACKAGE", "com.rokid.sprite.global.aiapp") # Default package

def start_collector():
    logs_dir = os.path.join(PROJECT_DIR, "logs")
    data_dir = os.path.join(PROJECT_DIR, "data")
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    out_file = os.path.join(logs_dir, "collector.out")
    pid_file = os.path.join(logs_dir, "collector.pid")

    print(f"[info] starting collector... logs: {out_file}")

    # Command to run android_collector.py
    cmd = [
        PYTHON_EXECUTABLE,
        "-u",  # Unbuffered output
        "-m",
        "collector.android_collector"
    ]

    # Set environment variables for the subprocess
    env = os.environ.copy()
    env["APP_PACKAGE"] = APP_PACKAGE
    # Add other environment variables from existing config if any, e.g., ADB_SERIAL, SAMPLE_INTERVAL_SECONDS
    # For now, we'll rely on android_collector.py to load them from .env if available.

    with open(out_file, "w") as outfile:
        process = subprocess.Popen(
            cmd,
            stdout=outfile,
            stderr=outfile,
            env=env,
            preexec_fn=os.setsid # Detach from current process group
        )
    
    with open(pid_file, "w") as f:
        f.write(str(process.pid))

    print(f"[ok] collector started. PID written to {pid_file}")

if __name__ == "__main__":
    start_collector()
