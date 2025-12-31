import os
import subprocess
import sys

# Define project directory dynamically
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)

VENV_PATH = os.path.join(PROJECT_DIR, ".venv")
PYTHON_EXECUTABLE = os.path.join(VENV_PATH, "bin", "python")
STREAMLIT_EXECUTABLE = os.path.join(VENV_PATH, "bin", "streamlit")

def run_visualizer():
    print("[info] starting Streamlit app...")

    # Command to run visualizer/app.py with streamlit
    cmd = [
        STREAMLIT_EXECUTABLE,
        "run",
        os.path.join(PROJECT_DIR, "visualizer", "app.py"),
        "--server.address", "localhost",
        "--server.port", "8501",
        "--browser.serverAddress", "localhost"
    ]

    # Ensure the virtual environment's python is used if not already in path
    env = os.environ.copy()
    env["PATH"] = os.path.join(VENV_PATH, "bin") + os.pathsep + env["PATH"]

    # Run Streamlit in the foreground
    subprocess.run(cmd, env=env)

if __name__ == "__main__":
    run_visualizer()
