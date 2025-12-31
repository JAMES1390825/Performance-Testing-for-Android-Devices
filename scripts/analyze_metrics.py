#!/usr/bin/env python3
"""
性能数据分析工具
分析采集的 App 性能数据，生成报告
"""

import os
import sys
import glob
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"


def load_latest_data():
    """加载最新的数据文件"""
    files = sorted(glob.glob(str(DATA_DIR / "metrics_*.csv")))
    if not files:
        print("❌ 未找到数据文件")
        return None
    
    latest = files[-1]
    print(f"📁 加载: {Path(latest).name}")
    
    df = pd.read_csv(latest)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def analyze_cpu(df):
    """分析 CPU 数据"""
    if "app_cpu_percent" not in df.columns:
        return None
    
    cpu = df["app_cpu_percent"].dropna()
    if cpu.empty:
        return None
    
    stats = {
        "mean": round(cpu.mean(), 2),
        "median": round(cpu.median(), 2),
        "p90": round(np.percentile(cpu, 90), 2),
        "p95": round(np.percentile(cpu, 95), 2),
        "max": round(cpu.max(), 2),
    }
    
    # 评级
    if stats["mean"] < 15:
        stats["grade"] = "优秀"
    elif stats["mean"] < 30:
        stats["grade"] = "良好"
    elif stats["mean"] < 50:
        stats["grade"] = "一般"
    else:
        stats["grade"] = "较差"
    
    return stats


def analyze_memory(df):
    """分析内存数据"""
    if "app_mem_kb" not in df.columns:
        return None
    
    mem = df["app_mem_kb"].dropna() / 1024  # 转为 MB
    if mem.empty:
        return None
    
    stats = {
        "mean_mb": round(mem.mean(), 1),
        "median_mb": round(mem.median(), 1),
        "p90_mb": round(np.percentile(mem, 90), 1),
        "max_mb": round(mem.max(), 1),
        "min_mb": round(mem.min(), 1),
    }
    
    # 内存增长分析
    if len(mem) >= 10:
        start_mem = mem.iloc[:5].mean()
        end_mem = mem.iloc[-5:].mean()
        duration_hours = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).total_seconds() / 3600
        
        if duration_hours > 0:
            growth_rate = (end_mem - start_mem) / duration_hours
            stats["growth_mb_per_hour"] = round(growth_rate, 2)
            
            if growth_rate > 30:
                stats["leak_warning"] = "严重泄漏风险"
            elif growth_rate > 15:
                stats["leak_warning"] = "轻微泄漏风险"
            else:
                stats["leak_warning"] = None
    
    # 评级
    if stats["mean_mb"] < 150:
        stats["grade"] = "优秀"
    elif stats["mean_mb"] < 250:
        stats["grade"] = "良好"
    elif stats["mean_mb"] < 400:
        stats["grade"] = "一般"
    else:
        stats["grade"] = "较差"
    
    return stats


def analyze_fps(df):
    """分析 FPS 数据"""
    result = {}
    
    if "fps" in df.columns:
        fps = df["fps"].dropna()
        if not fps.empty:
            result["fps_mean"] = round(fps.mean(), 1)
            result["fps_min"] = round(fps.min(), 1)
            result["fps_p10"] = round(np.percentile(fps, 10), 1)  # 最差 10%
    
    if "jank_rate" in df.columns:
        jank = df["jank_rate"].dropna()
        if not jank.empty:
            result["jank_rate_mean"] = round(jank.mean(), 2)
            result["jank_rate_max"] = round(jank.max(), 2)
    
    if not result:
        return None
    
    # 评级
    fps_mean = result.get("fps_mean", 60)
    jank_mean = result.get("jank_rate_mean", 0)
    
    if fps_mean >= 55 and jank_mean < 2:
        result["grade"] = "优秀"
    elif fps_mean >= 50 and jank_mean < 5:
        result["grade"] = "良好"
    elif fps_mean >= 45:
        result["grade"] = "一般"
    else:
        result["grade"] = "较差"
    
    return result


def print_report(df):
    """打印分析报告"""
    print("\n" + "=" * 50)
    print("📊 App 性能分析报告")
    print("=" * 50)
    
    # 时间范围
    duration = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).total_seconds()
    print(f"\n⏱️  采集时长: {duration/60:.1f} 分钟 ({len(df)} 个数据点)")
    
    # CPU 分析
    cpu_stats = analyze_cpu(df)
    if cpu_stats:
        print(f"\n🔥 CPU 占用:")
        print(f"   平均: {cpu_stats['mean']}%")
        print(f"   P90: {cpu_stats['p90']}% | P95: {cpu_stats['p95']}%")
        print(f"   峰值: {cpu_stats['max']}%")
        print(f"   评级: {cpu_stats['grade']}")
    
    # 内存分析
    mem_stats = analyze_memory(df)
    if mem_stats:
        print(f"\n💾 内存占用:")
        print(f"   平均: {mem_stats['mean_mb']}MB")
        print(f"   P90: {mem_stats['p90_mb']}MB | 峰值: {mem_stats['max_mb']}MB")
        print(f"   评级: {mem_stats['grade']}")
        
        if "growth_mb_per_hour" in mem_stats:
            print(f"   增长率: {mem_stats['growth_mb_per_hour']}MB/小时")
            if mem_stats.get("leak_warning"):
                print(f"   ⚠️  {mem_stats['leak_warning']}")
    
    # FPS 分析
    fps_stats = analyze_fps(df)
    if fps_stats:
        print(f"\n🎮 流畅度:")
        if "fps_mean" in fps_stats:
            print(f"   平均 FPS: {fps_stats['fps_mean']}")
            print(f"   最低 FPS: {fps_stats['fps_min']} | P10: {fps_stats['fps_p10']}")
        if "jank_rate_mean" in fps_stats:
            print(f"   平均卡顿率: {fps_stats['jank_rate_mean']}%")
        print(f"   评级: {fps_stats['grade']}")
    
    print("\n" + "=" * 50)
    
    return {
        "cpu": cpu_stats,
        "memory": mem_stats,
        "fps": fps_stats,
    }


def main():
    """主函数"""
    df = load_latest_data()
    if df is None:
        return
    
    report = print_report(df)
    
    # 保存报告
    report_file = DATA_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"📁 报告已保存: {report_file.name}")


if __name__ == "__main__":
    main()
