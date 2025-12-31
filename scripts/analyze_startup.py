#!/usr/bin/env python3
"""
启动时间自动化测试工具
支持冷启动、热启动测试，自动输出报告
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv()


class StartupTester:
    """启动时间测试器"""
    
    def __init__(self, package_name=None, activity_name=None):
        self.package_name = package_name or os.getenv("APP_PACKAGE")
        self.activity_name = activity_name or os.getenv("APP_ACTIVITY", ".MainActivity")
        self.adb_serial = os.getenv("ADB_SERIAL")
        self.adb_prefix = ["adb", "-s", self.adb_serial] if self.adb_serial else ["adb"]
        
        if not self.package_name:
            raise ValueError("请设置 APP_PACKAGE 环境变量")
    
    def _adb(self, args):
        """执行 adb 命令"""
        cmd = self.adb_prefix + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout, result.returncode
    
    def _parse_start_result(self, output):
        """解析 am start -W 输出"""
        result = {}
        for line in output.split('\n'):
            if "ThisTime:" in line:
                result["this_time"] = int(line.split(":")[1].strip())
            elif "TotalTime:" in line:
                result["total_time"] = int(line.split(":")[1].strip())
            elif "WaitTime:" in line:
                result["wait_time"] = int(line.split(":")[1].strip())
        return result
    
    def measure_cold_start(self, iterations=5):
        """
        测量冷启动时间
        冷启动：进程不存在，从头启动
        """
        print(f"\n[冷启动测试]")
        print(f"   包名: {self.package_name}")
        print(f"   Activity: {self.activity_name}")
        print(f"   测试次数: {iterations}")
        print("-" * 50)
        
        results = []
        component = f"{self.package_name}/{self.activity_name}"
        
        for i in range(iterations):
            # 强制停止应用
            self._adb(["shell", "am", "force-stop", self.package_name])
            time.sleep(2)
            
            # 启动应用
            output, _ = self._adb(["shell", "am", "start", "-W", "-n", component])
            parsed = self._parse_start_result(output)
            
            if "total_time" in parsed:
                results.append(parsed)
                print(f"   [{i+1}/{iterations}] TotalTime: {parsed['total_time']}ms")
            else:
                print(f"   [{i+1}/{iterations}] 失败")
            
            time.sleep(2)
        
        return self._analyze_results(results, "冷启动")
    
    def measure_warm_start(self, iterations=5):
        """
        测量热启动时间
        热启动：进程存在，Activity 需要重建
        """
        print(f"\n[热启动测试]")
        print(f"   包名: {self.package_name}")
        print(f"   测试次数: {iterations}")
        print("-" * 50)
        
        component = f"{self.package_name}/{self.activity_name}"
        
        # 先启动一次
        self._adb(["shell", "am", "start", "-n", component])
        time.sleep(3)
        
        results = []
        
        for i in range(iterations):
            # 按 Home 键回到桌面
            self._adb(["shell", "input", "keyevent", "3"])
            time.sleep(1)
            
            # 重新启动
            output, _ = self._adb(["shell", "am", "start", "-W", "-n", component])
            parsed = self._parse_start_result(output)
            
            if "total_time" in parsed:
                results.append(parsed)
                print(f"   [{i+1}/{iterations}] TotalTime: {parsed['total_time']}ms")
            else:
                print(f"   [{i+1}/{iterations}] 失败")
            
            time.sleep(1)
        
        return self._analyze_results(results, "热启动")
    
    def _analyze_results(self, results, test_type):
        """分析测试结果"""
        if not results:
            return None
        
        times = [r["total_time"] for r in results]
        avg = sum(times) / len(times)
        min_t = min(times)
        max_t = max(times)
        
        # 评估标准
        if test_type == "冷启动":
            thresholds = [(1500, "优秀"), (2500, "良好"), (4000, "一般")]
        else:  # 热启动
            thresholds = [(800, "优秀"), (1500, "良好"), (2500, "一般")]
        
        grade = "较差"
        for threshold, g in thresholds:
            if avg < threshold:
                grade = g
                break
        
        analysis = {
            "type": test_type,
            "iterations": len(results),
            "avg_ms": round(avg),
            "min_ms": min_t,
            "max_ms": max_t,
            "grade": grade,
            "raw_data": times,
        }
        
        print(f"\n[{test_type}结果]")
        print(f"   平均: {avg:.0f}ms ({avg/1000:.2f}s)")
        print(f"   最快: {min_t}ms | 最慢: {max_t}ms")
        print(f"   评级: {grade}")
        
        return analysis
    
    def run_full_test(self, iterations=5, save_report=True):
        """运行完整测试"""
        print("=" * 50)
        print("Android App 启动性能测试")
        print("=" * 50)
        
        cold = self.measure_cold_start(iterations)
        warm = self.measure_warm_start(iterations)
        
        report = {
            "package": self.package_name,
            "activity": self.activity_name,
            "test_time": datetime.now().isoformat(),
            "cold_start": cold,
            "warm_start": warm,
        }
        
        # 综合报告
        print("\n" + "=" * 50)
        print("[综合报告]")
        print("=" * 50)
        
        if cold and warm:
            print(f"\n   冷启动: {cold['avg_ms']}ms ({cold['grade']})")
            print(f"   热启动: {warm['avg_ms']}ms ({warm['grade']})")
            print(f"   差值: {cold['avg_ms'] - warm['avg_ms']}ms")
            print(f"\n   提示: 差值越大说明 Application 初始化耗时越多")
        
        # 保存报告
        if save_report:
            report_dir = PROJECT_DIR / "data"
            report_dir.mkdir(exist_ok=True)
            report_file = report_dir / f"startup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n   报告已保存: {report_file}")
        
        return report


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Android App 启动时间测试")
    parser.add_argument("-n", "--iterations", type=int, default=5, help="测试次数")
    parser.add_argument("-t", "--type", choices=["cold", "warm", "all"], default="all", help="测试类型")
    parser.add_argument("--no-save", action="store_true", help="不保存报告")
    
    args = parser.parse_args()
    
    try:
        tester = StartupTester()
    except ValueError as e:
        print(f"错误: {e}")
        return
    
    if args.type == "cold":
        tester.measure_cold_start(args.iterations)
    elif args.type == "warm":
        tester.measure_warm_start(args.iterations)
    else:
        tester.run_full_test(args.iterations, save_report=not args.no_save)


if __name__ == "__main__":
    main()
