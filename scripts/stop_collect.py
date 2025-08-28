import os
import signal
import sys
import time

# Define project directory dynamically
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)

def stop_collector():
    pid_file = os.path.join(PROJECT_DIR, "logs", "collector.pid")

    if not os.path.exists(pid_file):
        print("no pid file: {pid_file}")
        return

    with open(pid_file, "r") as f:
        pid = int(f.read().strip())
    
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"killing collector {pid}")
        # Give it a moment to terminate gracefully
        time.sleep(1)
        if os.path.exists(f"/proc/{pid}") or os.path.exists(f"/private/var/db/systemstats/state/{pid}"): # For macOS and Linux
            os.kill(pid, signal.SIGKILL)
            print(f"force kill {pid}")
    except ProcessLookupError:
        print(f"collector process {pid} not found, already stopped?")
    except Exception as e:
        print(f"Error stopping collector: {e}")
    
    if os.path.exists(pid_file):
        os.remove(pid_file)
    print("stopped.")

if __name__ == "__main__":
    stop_collector()
