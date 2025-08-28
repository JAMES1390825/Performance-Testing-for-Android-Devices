采集字段说明

- timestamp: ISO 时间戳（本机时间）
- total_cpu_percent: 设备总 CPU 占用（%），来自 `dumpsys cpuinfo`/`top` 粗略估计
- mem_total_kb: 总内存（kB），来自 `/proc/meminfo`
- mem_available_kb: 可用内存（kB），来自 `/proc/meminfo`
- mem_used_percent: 估算内存使用率（%）= (1 - Available/Total) * 100
- battery_level: 电量等级（%），来自 `dumpsys battery`
- battery_temp_c: 电池温度（℃），来自 `dumpsys battery`（原始 0.1℃ 单位已换算）
- app_cpu_percent: 指定包名进程 CPU 占用（%），若 `.env` 未配置 `APP_PACKAGE` 则为空
- app_mem_kb: 指定包名进程内存（kB PSS），若未配置则为空

注：CPU 指标基于系统命令快照估算，非高精度分析；若需更精细统计可按需改为基于 `/proc/stat` 取两次样计算。

