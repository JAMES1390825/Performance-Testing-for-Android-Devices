import csv
import os
import signal
import sys
import time
import subprocess
from datetime import datetime

from dotenv import load_dotenv


def load_config():
    load_dotenv()
    config = {
        "adb_serial": os.getenv("ADB_SERIAL", ""),
        "interval": float(os.getenv("SAMPLE_INTERVAL_SECONDS", "1.0")),
        "app_package": os.getenv("APP_PACKAGE", ""),
        "data_dir": os.getenv("DATA_DIR", "/Users/xujinliang/Desktop/AndroidPerfMon/data"),
        "log_dir": os.getenv("LOG_DIR", "/Users/xujinliang/Desktop/AndroidPerfMon/logs"),
    }
    os.makedirs(config["data_dir"], exist_ok=True)
    os.makedirs(config["log_dir"], exist_ok=True)
    return config


def adb_shell(command_parts, adb_serial):
    base = ["adb"]
    if adb_serial:
        base += ["-s", adb_serial]
    base += ["shell"] + command_parts
    try:
        out = subprocess.check_output(base, stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="ignore")
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8", errors="ignore")


def parse_total_cpu_percent(text):
    # Try dumpsys cpuinfo style lines containing TOTAL/Total
    percent = None
    for line in text.splitlines():
        if "TOTAL" in line or line.strip().startswith("Total"):
            # find first number before %
            tokens = [t for t in line.replace("/", " ").replace(",", " ").split() if t]
            for tok in tokens:
                if tok.endswith("%") and tok[:-1].replace(".", "", 1).isdigit():
                    try:
                        percent = float(tok[:-1])
                        return percent
                    except Exception:
                        pass
    # Try top summary line: "CPU usage from ...: 3% user + 2% kernel ..."
    for line in text.splitlines():
        if "CPU usage from" in line and "%" in line:
            nums = []
            for part in line.split():
                if part.endswith("%") and part[:-1].replace(".", "", 1).isdigit():
                    try:
                        nums.append(float(part[:-1]))
                    except Exception:
                        pass
            if nums:
                return sum(nums)
    return percent


def parse_meminfo(text):
    mem_total = None
    mem_available = None
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                mem_total = int(parts[1])
        elif line.startswith("MemAvailable:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                mem_available = int(parts[1])
    mem_used_percent = None
    if mem_total and mem_available is not None and mem_total > 0:
        mem_used_percent = (1.0 - (mem_available / float(mem_total))) * 100.0
    return mem_total, mem_available, mem_used_percent


def parse_battery(text):
    level = None
    temp_c = None
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("level:"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                val = parts[1].strip()
                if val.isdigit():
                    level = int(val)
        elif line.lower().startswith("temperature:"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                raw = parts[1].strip()
                try:
                    tenths = int(raw)
                    temp_c = tenths / 10.0
                except Exception:
                    pass
    return level, temp_c


def parse_app_cpu_from_cpuinfo(text, package_name):
    if not package_name:
        return None
    best = None
    for line in text.splitlines():
        # Look for lines like: "  16% 23856/com.rokid.sprite.global.aiapp: ..."
        if package_name in line and "%" in line:
            parts = line.strip().split()
            if len(parts) > 0 and parts[0].endswith("%"):
                try:
                    val = float(parts[0][:-1])
                    return val  # Return the first percentage found in the line
                except ValueError:
                    continue
    return best


def parse_app_mem_from_meminfo(text):
    # Look for line starts with TOTAL after "Applications Memory Usage (in Kilobytes):"
    for line in text.splitlines():
        if line.strip().startswith("TOTAL"):
            parts = line.split()
            # common format: TOTAL PSS: <kb> ... or just TOTAL <kb>
            for part in parts:
                if part.isdigit():
                    return int(part)
    return None


def collect_once(cfg):
    serial = cfg["adb_serial"]

    cpuinfo = adb_shell(["dumpsys", "cpuinfo"], serial)
    total_cpu = parse_total_cpu_percent(cpuinfo)

    # Fallback with top if needed
    if total_cpu is None:
        top_out = adb_shell(["top", "-n", "1", "-b"], serial)
        total_cpu = parse_total_cpu_percent(top_out)

    meminfo_out = adb_shell(["cat", "/proc/meminfo"], serial)
    mem_total, mem_available, mem_used_percent = parse_meminfo(meminfo_out)

    battery_out = adb_shell(["dumpsys", "battery"], serial)
    battery_level, battery_temp_c = parse_battery(battery_out)

    app_cpu = None
    app_mem = None
    if cfg["app_package"]:
        print(f"[DEBUG] APP_PACKAGE: {cfg['app_package']}")
        cpuinfo = adb_shell(["dumpsys", "cpuinfo"], serial)
        app_cpu = parse_app_cpu_from_cpuinfo(cpuinfo, cfg["app_package"])
        print(f"[DEBUG] Parsed app_cpu: {app_cpu}")
        app_meminfo = adb_shell(["dumpsys", "meminfo", cfg["app_package"]], serial)
        app_mem = parse_app_mem_from_meminfo(app_meminfo)

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "total_cpu_percent": total_cpu,
        "mem_total_kb": mem_total,
        "mem_available_kb": mem_available,
        "mem_used_percent": mem_used_percent,
        "battery_level": battery_level,
        "battery_temp_c": battery_temp_c,
        "app_cpu_percent": app_cpu,
        "app_mem_kb": app_mem,
    }


def ensure_csv_writer(csv_path):
    is_new = not os.path.exists(csv_path)
    f = open(csv_path, mode="a", newline="")
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "timestamp",
            "total_cpu_percent",
            "mem_total_kb",
            "mem_available_kb",
            "mem_used_percent",
            "battery_level",
            "battery_temp_c",
            "app_cpu_percent",
            "app_mem_kb",
        ],
    )
    if is_new:
        writer.writeheader()
    return f, writer


def write_pid(pid_path):
    with open(pid_path, "w") as f:
        f.write(str(os.getpid()))


def main():
    cfg = load_config()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(cfg["data_dir"], f"metrics_{timestamp}.csv")
    pid_path = os.path.join(cfg["log_dir"], "collector.pid")
    write_pid(pid_path)

    stop_requested = False

    def handle_sigterm(signum, frame):
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, handle_sigterm)
    signal.signal(signal.SIGTERM, handle_sigterm)

    file_handle, writer = ensure_csv_writer(csv_path)
    try:
        while not stop_requested:
            row = collect_once(cfg)
            writer.writerow(row)
            file_handle.flush()
            time.sleep(max(0.05, cfg["interval"]))
    finally:
        file_handle.close()
        # do not remove pid on exit to allow post-mortem. stop script will clean.


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)

