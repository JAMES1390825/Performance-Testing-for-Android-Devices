#!/usr/bin/env python3
"""
Android App 性能数据采集器
专注于应用级指标：CPU、内存、FPS
"""

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
        "data_dir": os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")),
        "log_dir": os.getenv("LOG_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")),
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
        out = subprocess.check_output(base, stderr=subprocess.STDOUT, timeout=10)
        return out.decode("utf-8", errors="ignore")
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8", errors="ignore")
    except subprocess.TimeoutExpired:
        return ""


def parse_app_cpu_from_top(text, package_name):
    """
    从 top 命令解析应用 CPU 占用（更准确）
    top 输出格式: PID USER PR NI VIRT RES SHR S %CPU %MEM TIME+ ARGS
    """
    if not package_name:
        return None
    
    for line in text.splitlines():
        if package_name in line:
            parts = line.split()
            # top 输出通常是: PID USER ... %CPU %MEM ... COMMAND
            # 找到包含数字和%的列
            for i, part in enumerate(parts):
                # 跳过 PID（第一列纯数字）
                if i == 0:
                    continue
                # CPU 通常在第 8 或 9 列，是一个数字
                try:
                    val = float(part)
                    # CPU 值通常在 0-100+ 范围，排除 PID 等大数字
                    if 0 <= val <= 800:  # 多核可能超过 100
                        return val
                except ValueError:
                    continue
    return None


def parse_app_mem(text):
    """从 dumpsys meminfo 解析应用内存 (PSS)"""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("TOTAL") and "TOTAL:" not in line:
            parts = line.split()
            for part in parts[1:]:
                if part.isdigit():
                    return int(part)
    return None


def parse_fps_from_gfxinfo(text):
    """
    从 dumpsys gfxinfo 解析 FPS 相关数据
    返回: (total_frames, janky_frames, jank_rate)
    """
    total_frames = None
    janky_frames = None
    
    for line in text.splitlines():
        line = line.strip()
        # Total frames rendered: 12345
        if "Total frames rendered:" in line:
            parts = line.split(":")
            if len(parts) >= 2:
                try:
                    total_frames = int(parts[1].strip())
                except ValueError:
                    pass
        # Janky frames: 123 (1.00%)
        elif "Janky frames:" in line:
            parts = line.split(":")
            if len(parts) >= 2:
                val = parts[1].strip().split()[0]
                try:
                    janky_frames = int(val)
                except ValueError:
                    pass
    
    # 计算卡顿率（只有帧数足够多时才计算，避免静止界面误报）
    jank_rate = None
    if total_frames and total_frames >= 10 and janky_frames is not None:
        jank_rate = (janky_frames / total_frames) * 100
    
    return total_frames, janky_frames, jank_rate


def parse_frame_stats(text):
    """
    解析 framestats 计算实时 FPS
    framestats 格式: 每行是一帧的时间戳数据
    """
    frame_times = []
    in_stats = False
    
    for line in text.splitlines():
        line = line.strip()
        if "---PROFILEDATA---" in line:
            in_stats = True
            continue
        if in_stats and line and not line.startswith("Flags"):
            parts = line.split(",")
            if len(parts) >= 2:
                try:
                    # 第一列是 Flags，第二列是 IntendedVsync
                    intended_vsync = int(parts[1])
                    if intended_vsync > 0:
                        frame_times.append(intended_vsync)
                except (ValueError, IndexError):
                    pass
    
    # 计算 FPS
    if len(frame_times) >= 2:
        # 时间单位是纳秒
        duration_ns = frame_times[-1] - frame_times[0]
        if duration_ns > 0:
            duration_s = duration_ns / 1e9
            fps = (len(frame_times) - 1) / duration_s
            return min(fps, 120)  # 限制最大值
    
    return None


def collect_once(cfg):
    """采集一次数据"""
    serial = cfg["adb_serial"]
    package = cfg["app_package"]
    
    if not package:
        print("[WARN] APP_PACKAGE 未配置")
        return None
    
    # 应用 CPU（使用 top 命令，更准确）
    top_output = adb_shell(["top", "-n", "1", "-b"], serial)
    app_cpu = parse_app_cpu_from_top(top_output, package)
    
    # 应用内存
    meminfo = adb_shell(["dumpsys", "meminfo", package], serial)
    app_mem = parse_app_mem(meminfo)
    
    # FPS 和卡顿
    gfxinfo = adb_shell(["dumpsys", "gfxinfo", package, "framestats"], serial)
    total_frames, janky_frames, jank_rate = parse_fps_from_gfxinfo(gfxinfo)
    fps = parse_frame_stats(gfxinfo)
    
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "app_cpu_percent": app_cpu,
        "app_mem_kb": app_mem,
        "fps": round(fps, 1) if fps else None,
        "total_frames": total_frames,
        "janky_frames": janky_frames,
        "jank_rate": round(jank_rate, 2) if jank_rate else None,
    }


def ensure_csv_writer(csv_path):
    is_new = not os.path.exists(csv_path)
    f = open(csv_path, mode="a", newline="")
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "timestamp",
            "app_cpu_percent",
            "app_mem_kb",
            "fps",
            "total_frames",
            "janky_frames",
            "jank_rate",
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
    
    if not cfg["app_package"]:
        print("[ERROR] 请在 .env 中配置 APP_PACKAGE")
        sys.exit(1)
    
    print(f"[INFO] 开始采集: {cfg['app_package']}")
    print(f"[INFO] 采集间隔: {cfg['interval']}s")
    
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
            if row:
                writer.writerow(row)
                file_handle.flush()
                print(f"[DATA] CPU: {row['app_cpu_percent']}%, MEM: {row['app_mem_kb']}KB, FPS: {row['fps']}")
            time.sleep(max(0.1, cfg["interval"]))
    finally:
        file_handle.close()
        print(f"\n[INFO] 数据已保存: {csv_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
