Android 性能监控（CPU/内存/电量）采集与可视化

本项目旨在提供一个 Android 设备性能指标的采集与可视化解决方案。您可以轻松监控设备的 CPU、内存、电量等系统级指标，以及指定应用程序的 CPU 和内存占用情况。

## 快速开始

### 1. 克隆项目
首先，将项目从 GitHub 克隆到你的本地计算机：
```bash
git clone https://github.com/your-username/AndroidPerfMon.git # 请替换为你的实际项目地址
cd AndroidPerfMon
```

### 2. 先决条件
在运行项目之前，请确保满足以下条件：

-   **ADB (Android Debug Bridge)**：已安装 `adb` 工具，并且你的 Android 设备已通过 USB 线缆连接到电脑并开启了 USB 调试模式，或者通过网络成功连接（可以通过运行 `adb devices` 命令来确认设备是否被识别）。
-   **Python 3.9+**：macOS 系统通常自带 Python3，但建议确保安装的是 Python 3.9 或更高版本。

### 3. 安装依赖与环境配置

#### 推荐方式 (使用虚拟环境)
强烈建议在虚拟环境中安装项目依赖，以避免与系统其他 Python 环境冲突，并保持环境的清洁与隔离。

```bash
# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装所有必要的 Python 库
pip install -r requirements.txt
```

#### 替代方式 (不使用虚拟环境)
如果你选择不使用虚拟环境，所有依赖将安装到你的全局 Python 环境中。**请注意，这可能会导致与其他 Python 项目或系统工具的依赖冲突。**

```bash
# 全局安装所有必要的 Python 库
pip install -r requirements.txt
```

### 4. 配置环境变量 (`.env` 文件)
在项目根目录下创建一个名为 `.env` 的文件（如果不存在），并根据你的需求配置以下环境变量。`android_collector.py` 脚本会自动加载这些配置。

-   **`ADB_SERIAL`** (可选): 当你连接了多台 Android 设备时，你需要指定要监控的具体设备的序列号。你可以通过 `adb devices` 命令获取设备序列号。例如：`ADB_SERIAL=emulator-5554`。如果只连接了一台设备，可以不设置此项。
-   **`SAMPLE_INTERVAL_SECONDS`** (可选): 设置数据采集的间隔时间，单位为秒。例如：`SAMPLE_INTERVAL_SECONDS=5.0` 将每 5 秒采集一次数据。默认值为 `1.0` 秒。
-   **`APP_PACKAGE`** (可选): 指定一个你希望单独监控性能的 Android 应用程序的完整包名（例如：`com.rokid.sprite.global.aiapp`）。如果设置此项，可视化界面将显示该应用的 CPU 和内存专用图表。如果未设置，则不采集应用维度数据。

**示例 `.env` 文件内容：**
```
ADB_SERIAL=your_device_serial_here # 替换为你的设备序列号
SAMPLE_INTERVAL_SECONDS=5.0
APP_PACKAGE=com.rokid.sprite.global.aiapp # 替换为你要监控的应用包名
```

### 5. 运行项目
请确保在运行以下脚本之前，你的 Android 设备已正确连接并开启 USB 调试。

**重要提示**：
*   如果你使用的是**推荐方式（虚拟环境）**，请确保在运行脚本前**激活虚拟环境** (`source .venv/bin/activate`)。
*   如果你使用的是**替代方式（不使用虚拟环境）**，直接运行 `python` 命令即可。

**a. 启动数据采集**
运行以下命令启动数据采集脚本。采集器将在后台持续运行，并将数据写入 `data/` 目录下的 CSV 文件，日志输出到 `logs/collector.out`。

```bash
python scripts/start_collect.py
```

**b. 停止数据采集**
当你需要停止数据采集时，运行以下命令：

```bash
python scripts/stop_collect.py
```

**c. 启动可视化界面**
运行以下命令启动 Streamlit 可视化应用。应用启动后，你可以在浏览器中访问显示的本地 URL（通常是 `http://localhost:8501`）查看性能折线图。

```bash
python scripts/run_visualizer.py
```

**图表说明：**
*   在可视化界面中，你可以通过侧边栏切换不同的数据文件和调整刷新周期。
*   “应用维度”下的 CPU 和内存数据现在会显示为独立的折线图，更清晰地展示指定应用的性能。

## 更多信息

关于采集到的各项性能指标的详细说明，请查阅 `docs/metrics.md`。

