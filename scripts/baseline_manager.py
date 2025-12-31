#!/usr/bin/env python3
"""
性能基线管理工具
用于创建、更新和对比性能基线
"""

import os
import sys
import json
import glob
import shutil
import pandas as pd
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

DATA_DIR = os.environ.get("DATA_DIR", str(PROJECT_DIR / "data"))
BASELINE_DIR = PROJECT_DIR / "baselines"
BASELINE_DIR.mkdir(exist_ok=True)


def create_baseline(name, description=""):
    """创建性能基线"""
    # 获取最新的数据文件
    files = sorted(glob.glob(os.path.join(DATA_DIR, "metrics_*.csv")))
    if not files:
        print("❌ 未找到数据文件")
        return False
    
    latest_file = files[-1]
    print(f"📁 使用数据文件: {os.path.basename(latest_file)}")
    
    # 加载数据
    try:
        df = pd.read_csv(latest_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return False
    
    # 计算基线指标
    baseline_metrics = {}
    
    if "app_cpu_percent" in df.columns:
        cpu_data = df["app_cpu_percent"].dropna()
        if len(cpu_data) > 0:
            baseline_metrics["cpu"] = {
                "mean": float(cpu_data.mean()),
                "median": float(cpu_data.median()),
                "p90": float(cpu_data.quantile(0.90)),
                "p95": float(cpu_data.quantile(0.95)),
                "max": float(cpu_data.max()),
            }
    
    if "app_mem_kb" in df.columns:
        mem_data = df["app_mem_kb"].dropna()
        if len(mem_data) > 0:
            baseline_metrics["memory"] = {
                "mean": float(mem_data.mean()),
                "median": float(mem_data.median()),
                "p90": float(mem_data.quantile(0.90)),
                "p95": float(mem_data.quantile(0.95)),
                "max": float(mem_data.max()),
            }
    
    if "battery_level" in df.columns:
        battery_data = df["battery_level"].dropna()
        if len(battery_data) >= 2:
            start_time = df["timestamp"].iloc[0]
            end_time = df["timestamp"].iloc[-1]
            duration_hours = (end_time - start_time).total_seconds() / 3600
            
            if duration_hours > 0.1:
                start_battery = battery_data.iloc[0]
                end_battery = battery_data.iloc[-1]
                drain_rate = (start_battery - end_battery) / duration_hours
                
                baseline_metrics["battery"] = {
                    "drain_rate_per_hour": float(drain_rate),
                    "mean_level": float(battery_data.mean()),
                }
    
    if "battery_temp_c" in df.columns:
        temp_data = df["battery_temp_c"].dropna()
        if len(temp_data) > 0:
            baseline_metrics["temperature"] = {
                "mean": float(temp_data.mean()),
                "max": float(temp_data.max()),
            }
    
    # 创建基线记录
    baseline = {
        "name": name,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "source_file": os.path.basename(latest_file),
        "data_points": len(df),
        "duration_minutes": (df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 60,
        "metrics": baseline_metrics,
    }
    
    # 保存基线
    baseline_file = BASELINE_DIR / f"{name}.json"
    with open(baseline_file, "w") as f:
        json.dump(baseline, f, indent=2)
    
    # 复制原始数据
    data_file = BASELINE_DIR / f"{name}_data.csv"
    shutil.copy(latest_file, data_file)
    
    print(f"\n✅ 基线创建成功: {name}")
    print(f"   配置文件: {baseline_file}")
    print(f"   数据文件: {data_file}")
    print(f"\n基线指标:")
    
    if "cpu" in baseline_metrics:
        print(f"   CPU平均: {baseline_metrics['cpu']['mean']:.2f}%")
    if "memory" in baseline_metrics:
        print(f"   内存平均: {baseline_metrics['memory']['mean']/1024:.2f} MB")
    if "battery" in baseline_metrics:
        print(f"   电量消耗: {baseline_metrics['battery']['drain_rate_per_hour']:.2f}%/小时")
    
    return True


def list_baselines():
    """列出所有基线"""
    baseline_files = sorted(BASELINE_DIR.glob("*.json"))
    
    if not baseline_files:
        print("📭 暂无性能基线")
        return []
    
    print(f"\n📊 性能基线列表 (共 {len(baseline_files)} 个)")
    print("="*80)
    print(f"{'名称':<20} {'创建时间':<20} {'描述':<30}")
    print("-"*80)
    
    baselines = []
    for bf in baseline_files:
        try:
            with open(bf) as f:
                baseline = json.load(f)
                baselines.append(baseline)
                
                created = datetime.fromisoformat(baseline["created_at"])
                print(f"{baseline['name']:<20} {created.strftime('%Y-%m-%d %H:%M'):<20} {baseline.get('description', ''):<30}")
        except Exception as e:
            print(f"❌ 读取 {bf.name} 失败: {e}")
    
    print("="*80)
    return baselines


def show_baseline(name):
    """显示基线详情"""
    baseline_file = BASELINE_DIR / f"{name}.json"
    
    if not baseline_file.exists():
        print(f"❌ 基线不存在: {name}")
        return
    
    with open(baseline_file) as f:
        baseline = json.load(f)
    
    print(f"\n📊 基线详情: {name}")
    print("="*60)
    print(f"描述: {baseline.get('description', '无')}")
    print(f"创建时间: {baseline['created_at']}")
    print(f"数据来源: {baseline['source_file']}")
    print(f"数据点数: {baseline['data_points']}")
    print(f"时长: {baseline['duration_minutes']:.1f} 分钟")
    
    metrics = baseline["metrics"]
    
    if "cpu" in metrics:
        print(f"\n🔥 CPU指标:")
        print(f"   平均: {metrics['cpu']['mean']:.2f}%")
        print(f"   中位数: {metrics['cpu']['median']:.2f}%")
        print(f"   P90: {metrics['cpu']['p90']:.2f}%")
        print(f"   P95: {metrics['cpu']['p95']:.2f}%")
        print(f"   峰值: {metrics['cpu']['max']:.2f}%")
    
    if "memory" in metrics:
        print(f"\n💾 内存指标:")
        print(f"   平均: {metrics['memory']['mean']/1024:.2f} MB")
        print(f"   中位数: {metrics['memory']['median']/1024:.2f} MB")
        print(f"   P90: {metrics['memory']['p90']/1024:.2f} MB")
        print(f"   P95: {metrics['memory']['p95']/1024:.2f} MB")
        print(f"   峰值: {metrics['memory']['max']/1024:.2f} MB")
    
    if "battery" in metrics:
        print(f"\n🔋 电池指标:")
        print(f"   消耗率: {metrics['battery']['drain_rate_per_hour']:.2f}%/小时")
        print(f"   平均电量: {metrics['battery']['mean_level']:.1f}%")
    
    if "temperature" in metrics:
        print(f"\n🌡️  温度指标:")
        print(f"   平均: {metrics['temperature']['mean']:.1f}°C")
        print(f"   峰值: {metrics['temperature']['max']:.1f}°C")


def compare_with_baseline(baseline_name):
    """与基线对比当前数据"""
    # 加载基线
    baseline_file = BASELINE_DIR / f"{baseline_name}.json"
    if not baseline_file.exists():
        print(f"错误: 基线不存在: {baseline_name}")
        return
    
    with open(baseline_file) as f:
        baseline = json.load(f)
    
    # 加载当前数据
    files = sorted(glob.glob(os.path.join(DATA_DIR, "metrics_*.csv")))
    if not files:
        print("错误: 未找到当前数据文件")
        return
    
    latest_file = files[-1]
    try:
        df = pd.read_csv(latest_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    except Exception as e:
        print(f"错误: 读取文件失败: {e}")
        return
    
    print(f"\n[性能对比分析]")
    print("=" * 80)
    print(f"基线: {baseline_name} ({baseline['created_at'][:10]})")
    print(f"当前: {os.path.basename(latest_file)}")
    print("=" * 80)
    
    baseline_metrics = baseline["metrics"]
    
    # CPU 对比
    if "cpu" in baseline_metrics and "app_cpu_percent" in df.columns:
        cpu_data = df["app_cpu_percent"].dropna()
        if len(cpu_data) > 0:
            current = {
                "mean": float(cpu_data.mean()),
                "p90": float(cpu_data.quantile(0.90)),
                "p95": float(cpu_data.quantile(0.95)),
                "max": float(cpu_data.max()),
            }
            base = baseline_metrics["cpu"]
            
            print(f"\n[CPU 占用]")
            print(f"{'指标':<10} {'基线':<12} {'当前':<12} {'差异':<15} {'评估':<10}")
            print("-" * 60)
            
            for key, label in [("mean", "平均"), ("p90", "P90"), ("p95", "P95"), ("max", "峰值")]:
                b_val = base[key]
                c_val = current[key]
                diff = c_val - b_val
                diff_pct = (diff / b_val * 100) if b_val > 0 else 0
                
                if abs(diff_pct) < 5:
                    status = "稳定"
                elif diff_pct > 15:
                    status = "!! 回归"
                elif diff_pct > 5:
                    status = "! 轻微回归"
                elif diff_pct < -10:
                    status = "++ 提升"
                else:
                    status = "+ 轻微提升"
                
                print(f"{label:<10} {b_val:<12.2f} {c_val:<12.2f} {diff:+.2f} ({diff_pct:+.1f}%)   {status}")
    
    # 内存对比
    if "memory" in baseline_metrics and "app_mem_kb" in df.columns:
        mem_data = df["app_mem_kb"].dropna()
        if len(mem_data) > 0:
            current = {
                "mean": float(mem_data.mean()),
                "p90": float(mem_data.quantile(0.90)),
                "p95": float(mem_data.quantile(0.95)),
                "max": float(mem_data.max()),
            }
            base = baseline_metrics["memory"]
            
            print(f"\n[内存占用] (MB)")
            print(f"{'指标':<10} {'基线':<12} {'当前':<12} {'差异':<15} {'评估':<10}")
            print("-" * 60)
            
            for key, label in [("mean", "平均"), ("p90", "P90"), ("p95", "P95"), ("max", "峰值")]:
                b_val = base[key] / 1024
                c_val = current[key] / 1024
                diff = c_val - b_val
                diff_pct = (diff / b_val * 100) if b_val > 0 else 0
                
                if abs(diff_pct) < 5:
                    status = "稳定"
                elif diff_pct > 15:
                    status = "!! 回归"
                elif diff_pct > 5:
                    status = "! 轻微回归"
                elif diff_pct < -10:
                    status = "++ 提升"
                else:
                    status = "+ 轻微提升"
                
                print(f"{label:<10} {b_val:<12.1f} {c_val:<12.1f} {diff:+.1f} ({diff_pct:+.1f}%)   {status}")
    
    # 综合评估
    print(f"\n[综合评估]")
    print("-" * 60)
    
    issues = []
    improvements = []
    
    if "cpu" in baseline_metrics and "app_cpu_percent" in df.columns:
        cpu_data = df["app_cpu_percent"].dropna()
        if len(cpu_data) > 0:
            mean_diff = (cpu_data.mean() - baseline_metrics["cpu"]["mean"]) / baseline_metrics["cpu"]["mean"] * 100
            p90_diff = (cpu_data.quantile(0.90) - baseline_metrics["cpu"]["p90"]) / baseline_metrics["cpu"]["p90"] * 100
            
            if mean_diff > 15 or p90_diff > 20:
                issues.append(f"CPU 性能回归 (平均 {mean_diff:+.1f}%, P90 {p90_diff:+.1f}%)")
            elif mean_diff < -10:
                improvements.append(f"CPU 性能提升 ({mean_diff:+.1f}%)")
    
    if "memory" in baseline_metrics and "app_mem_kb" in df.columns:
        mem_data = df["app_mem_kb"].dropna()
        if len(mem_data) > 0:
            mean_diff = (mem_data.mean() - baseline_metrics["memory"]["mean"]) / baseline_metrics["memory"]["mean"] * 100
            p90_diff = (mem_data.quantile(0.90) - baseline_metrics["memory"]["p90"]) / baseline_metrics["memory"]["p90"] * 100
            
            if mean_diff > 15 or p90_diff > 20:
                issues.append(f"内存占用增加 (平均 {mean_diff:+.1f}%, P90 {p90_diff:+.1f}%)")
            elif mean_diff < -10:
                improvements.append(f"内存占用降低 ({mean_diff:+.1f}%)")
    
    if issues:
        print("发现问题:")
        for issue in issues:
            print(f"  - {issue}")
    
    if improvements:
        print("性能提升:")
        for imp in improvements:
            print(f"  + {imp}")
    
    if not issues and not improvements:
        print("性能稳定，无明显变化")
    
    print("=" * 80)


def delete_baseline(name):
    """删除基线"""
    baseline_file = BASELINE_DIR / f"{name}.json"
    data_file = BASELINE_DIR / f"{name}_data.csv"
    
    if not baseline_file.exists():
        print(f"❌ 基线不存在: {name}")
        return
    
    baseline_file.unlink()
    if data_file.exists():
        data_file.unlink()
    
    print(f"✅ 基线已删除: {name}")


def main():
    """主函数"""
    print("📊 性能基线管理工具")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\n用法:")
        print("   python baseline_manager.py create <name> [description]  # 创建基线")
        print("   python baseline_manager.py list                         # 列出所有基线")
        print("   python baseline_manager.py show <name>                  # 显示基线详情")
        print("   python baseline_manager.py compare <name>               # 与基线对比")
        print("   python baseline_manager.py delete <name>                # 删除基线")
        print("\n示例:")
        print("   python baseline_manager.py create v1.0.0 '版本1.0.0性能基线'")
        print("   python baseline_manager.py compare v1.0.0")
        return
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("❌ 请指定基线名称")
            return
        name = sys.argv[2]
        description = sys.argv[3] if len(sys.argv) > 3 else ""
        create_baseline(name, description)
    
    elif command == "list":
        list_baselines()
    
    elif command == "show":
        if len(sys.argv) < 3:
            print("❌ 请指定基线名称")
            return
        show_baseline(sys.argv[2])
    
    elif command == "compare":
        if len(sys.argv) < 3:
            print("❌ 请指定基线名称")
            return
        compare_with_baseline(sys.argv[2])
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ 请指定基线名称")
            return
        delete_baseline(sys.argv[2])
    
    else:
        print(f"❌ 未知命令: {command}")


if __name__ == "__main__":
    main()
