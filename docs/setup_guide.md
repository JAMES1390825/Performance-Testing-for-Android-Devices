# 部署与使用指南

## 环境要求

- Python 3.9+
- ADB
- Android 设备（USB 调试已开启）

## 安装

```bash
git clone <repo-url>
cd AndroidPerfMon

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置

创建 `.env` 文件：

```
APP_PACKAGE=com.your.app
APP_ACTIVITY=.MainActivity
ADB_SERIAL=
SAMPLE_INTERVAL_SECONDS=1.0
```

- `APP_PACKAGE` - 必填，应用包名
- `APP_ACTIVITY` - 启动 Activity，用于启动测试
- `ADB_SERIAL` - 设备序列号，多设备时需要
- `SAMPLE_INTERVAL_SECONDS` - 采集间隔（秒）

## 使用

### 启动时间测试

测试应用冷启动和热启动时间：

```bash
# 完整测试（冷启动 + 热启动）
python scripts/analyze_startup.py

# 只测冷启动
python scripts/analyze_startup.py -t cold

# 只测热启动
python scripts/analyze_startup.py -t warm

# 指定测试次数
python scripts/analyze_startup.py -n 10
```

### 实时数据采集

采集应用运行时的 CPU、内存、FPS 数据：

```bash
# 启动采集
python scripts/start_collect.py

# 停止采集
python scripts/stop_collect.py
```

数据保存在 `data/metrics_*.csv`

> 注：FPS 和卡顿率只有在应用有 UI 操作时才会有数据，建议配合 UI 自动化测试使用。

### 性能分析

分析采集的数据，生成统计报告：

```bash
python scripts/analyze_metrics.py
```

### 可视化

启动 Web 界面查看实时图表：

```bash
python scripts/run_visualizer.py
# 打开 http://localhost:8501
```

界面包含 4 个图表：CPU 占用、内存占用、FPS、卡顿率。

### 基线管理

保存和对比性能数据：

```bash
# 创建基线
python scripts/baseline_manager.py create v1.0 "版本1.0"

# 列出基线
python scripts/baseline_manager.py list

# 查看基线
python scripts/baseline_manager.py show v1.0

# 对比基线
python scripts/baseline_manager.py compare v1.0

# 删除基线
python scripts/baseline_manager.py delete v1.0
```

## 数据文件

| 路径 | 说明 |
|------|------|
| `data/metrics_*.csv` | 采集数据 |
| `data/startup_*.json` | 启动测试报告 |
| `baselines/*.json` | 基线数据 |
